"""LangGraph agent node implementations."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agents.events import make_event
from backend.app.agents.prompts import RESPONSE_PROMPT, SUPERVISOR_PROMPT
from backend.app.agents.rlm import run_rlm_pipeline
from backend.app.agents.state import AgentState, Route
from backend.app.llm.provider import get_chat_llm
from backend.app.observability.langsmith_config import build_run_config
from backend.app.retrieval import HybridRetriever
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit
from backend.app.tools.registry import build_tool_node, build_tools, run_tool_node

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
        self._tools = build_tools(retriever)
        self._tool_node = build_tool_node(retriever)
        self._knowledge_search = next(
            tool for tool in self._tools if tool.name == "knowledge_search"
        )

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
        raw = await self._knowledge_search.ainvoke(
            {
                "query": state["user_question"],
                "top_k": 5,
                "department": state.get("department"),
                "document_type": state.get("document_type"),
                "user_role": state.get("user_role", "viewer"),
            }
        )
        docs = json.loads(raw)

        return {
            "retrieved_docs": docs,
            "current_node": "retrieval",
            "tool_calls": [
                {
                    "tool": "knowledge_search",
                    "query": state["user_question"],
                    "result_count": len(docs),
                }
            ],
            "agent_events": [
                make_event(
                    "retrieval",
                    "retrieval_complete",
                    f"knowledge_search returned {len(docs)} document chunks",
                    top_sources=[d.get("source_file") for d in docs[:3]],
                )
            ],
        }

    async def tools(self, state: AgentState) -> dict[str, Any]:
        return await run_tool_node(state, self._tool_node)

    async def research(self, state: AgentState) -> dict[str, Any]:
        question = state["user_question"]
        rlm_result = await run_rlm_pipeline(
            question=question,
            state=state,
            retriever=self._retriever,
        )

        batch_summaries = [
            {
                "batch_id": r.batch.batch_id,
                "focus": r.batch.focus,
                "query": r.batch.query,
                "chunk_count": len(r.docs),
                "summary": r.summary,
            }
            for r in rlm_result.batch_results
        ]

        return {
            "sub_queries": [b.query for b in rlm_result.plan.batches],
            "research_plan": {
                "objective": rlm_result.plan.objective,
                "batches": [
                    {"id": b.batch_id, "query": b.query, "focus": b.focus}
                    for b in rlm_result.plan.batches
                ],
            },
            "batch_summaries": batch_summaries,
            "retrieved_docs": rlm_result.retrieved_docs,
            "research_notes": rlm_result.research_notes,
            "current_node": "research",
            "agent_events": rlm_result.agent_events,
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
        batch_summaries = state.get("batch_summaries") or []
        extra_parts = []
        if research_notes:
            extra_parts.append(f"Research notes:\n{research_notes}")
        if batch_summaries:
            partials = "\n".join(
                f"- [{b.get('batch_id')}] {b.get('summary', '')[:300]}"
                for b in batch_summaries
            )
            extra_parts.append(f"Batch partial summaries:\n{partials}")
        analysis_results = state.get("analysis_results")
        if analysis_results:
            extra_parts.append(f"Tool analysis results:\n{analysis_results}")
        extra = f"\n\n{chr(10).join(extra_parts)}" if extra_parts else ""

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
