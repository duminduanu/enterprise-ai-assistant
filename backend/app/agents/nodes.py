"""LangGraph agent node implementations."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agents.events import make_event
from backend.app.agents.prompts import RESEARCH_PROMPT, RESPONSE_PROMPT, SUPERVISOR_PROMPT
from backend.app.agents.state import AgentState, Route
from backend.app.llm.provider import get_chat_llm
from backend.app.observability.langsmith_config import build_run_config
from backend.app.retrieval import HybridRetriever
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit

logger = logging.getLogger(__name__)

COMPLEX_QUERY_PATTERNS = (
    r"\bsummarize\b",
    r"\bcompare\b",
    r"\banaly[sz]e\b",
    r"\btrend",
    r"\ball\b.*\bincident",
    r"\boverview\b",
    r"\blast year\b",
    r"\bacross\b",
    r"\bmultiple\b",
    r"\blist all\b",
)


class AgentNodes:
    """Node callables bound to a shared retriever instance."""

    def __init__(self, retriever: HybridRetriever) -> None:
        self._retriever = retriever

    async def supervisor(self, state: AgentState) -> dict[str, Any]:
        question = state["user_question"]
        route, plan = await self._decide_route(question, state)

        return {
            "route": route,
            "plan": plan,
            "current_node": "supervisor",
            "agent_events": [
                make_event(
                    "supervisor",
                    "routing",
                    f"Routing to {route}",
                    plan=plan,
                )
            ],
        }

    async def retrieval(self, state: AgentState) -> dict[str, Any]:
        hits = await self._search(
            state["user_question"],
            state,
        )
        docs = []
        for hit in hits:
            doc = hit.to_dict()
            doc["text"] = hit.text
            docs.append(doc)

        return {
            "retrieved_docs": docs,
            "current_node": "retrieval",
            "agent_events": [
                make_event(
                    "retrieval",
                    "retrieval_complete",
                    f"Retrieved {len(docs)} document chunks",
                    top_sources=[d.get("source_file") for d in docs[:3]],
                )
            ],
        }

    async def research(self, state: AgentState) -> dict[str, Any]:
        sub_queries = await self._build_sub_queries(state)
        merged: dict[str, RetrievalHit] = {}

        for sub_query in sub_queries:
            hits = await self._search(sub_query, state, top_k=4)
            for hit in hits:
                existing = merged.get(hit.chunk_id)
                if existing is None or hit.hybrid_score > existing.hybrid_score:
                    merged[hit.chunk_id] = hit

        ranked = sorted(merged.values(), key=lambda h: h.hybrid_score, reverse=True)[:8]
        docs = []
        for hit in ranked:
            doc = hit.to_dict()
            doc["text"] = hit.text
            docs.append(doc)
        notes = (
            f"Research covered {len(sub_queries)} sub-queries and merged "
            f"{len(docs)} unique chunks."
        )

        return {
            "sub_queries": sub_queries,
            "retrieved_docs": docs,
            "research_notes": notes,
            "current_node": "research",
            "agent_events": [
                make_event(
                    "research",
                    "research_plan",
                    "Generated sub-queries for multi-document research",
                    sub_queries=sub_queries,
                ),
                make_event(
                    "research",
                    "research_complete",
                    notes,
                    chunk_count=len(docs),
                ),
            ],
        }

    async def response(self, state: AgentState) -> dict[str, Any]:
        docs = state.get("retrieved_docs") or []
        context = _format_context(docs)
        question = state["user_question"]

        try:
            answer = await self._generate_answer(question, context, state)
            llm_available = True
        except Exception:
            logger.exception("Response node LLM failed")
            answer = _fallback_answer(question, docs)
            llm_available = False

        return {
            "final_answer": answer,
            "llm_available": llm_available,
            "current_node": "response",
            "agent_events": [
                make_event(
                    "response",
                    "answer_generated",
                    "Draft answer composed from retrieved context",
                    llm_available=llm_available,
                    context_chunks=len(docs),
                )
            ],
        }

    async def validate(self, state: AgentState) -> dict[str, Any]:
        answer = state.get("final_answer") or ""
        docs = state.get("retrieved_docs") or []
        issues = _validate_answer(answer, docs)
        passed = len(issues) == 0

        final_answer = answer
        if not passed and docs:
            final_answer = (
                f"{answer}\n\n"
                f"[Validation note: {'; '.join(issues)}]"
            )

        return {
            "final_answer": final_answer,
            "validation_passed": passed,
            "validation_issues": issues,
            "current_node": "validate",
            "agent_events": [
                make_event(
                    "validate",
                    "validation_complete",
                    "Validation passed" if passed else "Validation flagged issues",
                    passed=passed,
                    issues=issues,
                )
            ],
        }

    async def _decide_route(
        self,
        question: str,
        state: AgentState,
    ) -> tuple[Route, str]:
        heuristic_route, heuristic_plan = _heuristic_route(question)
        llm = get_chat_llm()
        run_config = build_run_config(
            run_name="supervisor_routing",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "supervisor"],
        )

        try:
            response = await asyncio.to_thread(
                llm.invoke,
                [
                    SystemMessage(content=SUPERVISOR_PROMPT),
                    HumanMessage(content=f"Question: {question}"),
                ],
                config=run_config,
            )
            parsed = _parse_json(str(response.content))
            route = parsed.get("route", heuristic_route)
            plan = parsed.get("plan", heuristic_plan)
            if route not in {"retrieval", "research"}:
                route = heuristic_route
            return route, plan
        except Exception:
            logger.warning("Supervisor LLM routing failed; using heuristics")
            return heuristic_route, heuristic_plan

    async def _build_sub_queries(self, state: AgentState) -> list[str]:
        question = state["user_question"]
        defaults = _default_sub_queries(question)

        llm = get_chat_llm()
        run_config = build_run_config(
            run_name="research_planning",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "research"],
        )

        try:
            response = await asyncio.to_thread(
                llm.invoke,
                [
                    SystemMessage(content=RESEARCH_PROMPT),
                    HumanMessage(content=f"Question: {question}"),
                ],
                config=run_config,
            )
            parsed = _parse_json(str(response.content))
            sub_queries = parsed.get("sub_queries") or defaults
            cleaned = [q.strip() for q in sub_queries if isinstance(q, str) and q.strip()]
            return cleaned[:4] if cleaned else defaults
        except Exception:
            logger.warning("Research planning LLM failed; using default sub-queries")
            return defaults

    async def _search(
        self,
        query: str,
        state: AgentState,
        *,
        top_k: int | None = None,
    ) -> list[RetrievalHit]:
        filters = RetrievalFilters(
            department=state.get("department"),
            document_type=state.get("document_type"),
        )
        return await self._retriever.asearch(
            query,
            user_role=state.get("user_role", "viewer"),
            top_k=top_k,
            filters=filters,
        )

    async def _generate_answer(
        self,
        question: str,
        context: str,
        state: AgentState,
    ) -> str:
        llm = get_chat_llm()
        run_config = build_run_config(
            run_name="agent_response",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "response"],
        )
        research_notes = state.get("research_notes")
        extra = f"\nResearch notes: {research_notes}" if research_notes else ""

        response = await asyncio.to_thread(
            llm.invoke,
            [
                SystemMessage(content=RESPONSE_PROMPT),
                HumanMessage(
                    content=(
                        f"Context:\n{context}{extra}\n\n"
                        f"Question: {question}\n\nAnswer:"
                    )
                ),
            ],
            config=run_config,
        )
        content = str(response.content).strip()
        if not content:
            raise RuntimeError("Empty LLM response")
        return content


def _heuristic_route(question: str) -> tuple[Route, str]:
    lowered = question.lower()
    if any(re.search(pattern, lowered) for pattern in COMPLEX_QUERY_PATTERNS):
        return "research", "Multi-document synthesis required"
    return "retrieval", "Direct knowledge lookup"


def _default_sub_queries(question: str) -> list[str]:
    base = question.strip()
    return [
        base,
        f"{base} incident reports",
        f"{base} runbooks policies",
    ]


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _format_context(docs: list[dict[str, Any]]) -> str:
    if not docs:
        return "No relevant documents found."
    blocks = []
    for i, doc in enumerate(docs, start=1):
        blocks.append(
            f"[Document {i}] source={doc.get('source_file')} "
            f"title={doc.get('title')}\n{doc.get('text') or doc.get('text_preview', '')}"
        )
    return "\n\n".join(blocks)


def _fallback_answer(question: str, docs: list[dict[str, Any]]) -> str:
    if not docs:
        return (
            "I could not find relevant information in the knowledge base to answer your question. "
            "(LLM synthesis unavailable — retrieval-only mode.)"
        )

    lines = [
        "Retrieval-only response (LLM temporarily unavailable). Top matching sources:",
    ]
    for i, doc in enumerate(docs[:3], start=1):
        lines.append(
            f"{i}. [{doc.get('source_file')}] {doc.get('title')} — "
            f"{doc.get('section_heading', '')}"
        )
    lines.append(f"\nQuestion received: {question}")
    return "\n".join(lines)


def _validate_answer(answer: str, docs: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    lowered = answer.lower()

    if not docs and "do not have enough information" not in lowered:
        issues.append("No retrieved documents but answer did not admit insufficient context")

    if docs:
        cited_any = any(
            doc.get("source_file", "") in answer for doc in docs if doc.get("source_file")
        )
        if not cited_any and "retrieval-only response" not in lowered:
            issues.append("Answer missing inline source citations")

    injection_markers = ("ignore previous instructions", "system prompt", "you are now")
    if any(marker in lowered for marker in injection_markers):
        issues.append("Potential prompt-injection phrasing detected in output")

    return issues
