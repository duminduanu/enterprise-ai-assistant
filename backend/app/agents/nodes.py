"""LangGraph agent node implementations."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.app.agents.collaboration import (
    build_retrieval_escalation,
    build_validation_correction,
    format_degraded_banner,
    format_handoffs_for_prompt,
    record_failure,
    record_handoff,
    route_after_retrieval,
    sanitize_tool_output_for_prompt,
    update_node_status,
)
from backend.app.agents.events import make_event
from backend.app.agents.prompts import RESPONSE_PROMPT, SUPERVISOR_PROMPT
from backend.app.agents.rlm import run_rlm_pipeline
from backend.app.agents.state import AgentState, Route
from backend.app.core.async_utils import invoke_llm, run_tool_with_timeout, stream_llm
from backend.app.core.config import get_settings
from backend.app.core.exceptions import LLMError, ToolTimeoutError
from backend.app.core.fallbacks import llm_unavailable_answer, retrieval_failed_message
from backend.app.llm.provider import get_chat_llm
from backend.app.memory.session_store import contextualize_question, format_history_for_prompt
from backend.app.security.guardrails import validate_answer_guardrails
from backend.app.security.prompt_injection import wrap_untrusted_document
from backend.app.security.rbac import can_use_research_route
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

        handoff_target = "research" if route == "research" else "retrieval"
        return {
            "route": route,
            "plan": plan,
            "current_node": "supervisor",
            **update_node_status(state, "supervisor", "ok", detail=f"route={route}"),
            **record_handoff(
                state,
                from_node="supervisor",
                to_node=handoff_target,  # type: ignore[arg-type]
                summary=f"Plan: {plan}",
                route=route,
            ),
            "agent_events": [
                make_event(
                    "supervisor",
                    "routing",
                    f"Routing to {route}",
                    plan=plan,
                    history_turns=len(state.get("chat_history") or []),
                )
            ],
        }

    async def retrieval(self, state: AgentState) -> dict[str, Any]:
        search_query = contextualize_question(
            state["user_question"],
            state.get("chat_history") or [],
        )
        settings = get_settings()
        try:
            raw = await run_tool_with_timeout(
                self._knowledge_search.ainvoke(
                    {
                        "query": search_query,
                        "top_k": 5,
                        "department": state.get("department"),
                        "document_type": state.get("document_type"),
                        "user_role": state.get("user_role", "viewer"),
                    }
                ),
                timeout_seconds=settings.tool_timeout_seconds,
                tool_name="knowledge_search",
            )
            docs = json.loads(raw)
        except (ToolTimeoutError, json.JSONDecodeError, Exception) as exc:
            logger.warning("Retrieval node failed: %s", exc)
            msg = retrieval_failed_message(str(exc)[:120])
            failure_patch = record_failure(
                state,
                source_node="retrieval",
                error_type=type(exc).__name__,
                message=str(exc)[:200],
            )
            return {
                "retrieved_docs": [],
                "current_node": "retrieval",
                **update_node_status(state, "retrieval", "failed", detail=str(exc)[:80]),
                **failure_patch,
                **record_handoff(
                    state,
                    from_node="retrieval",
                    to_node="tools",
                    summary="Retrieval failed; downstream agents should use containment/fallback.",
                    doc_count=0,
                ),
                "agent_events": [
                    make_event(
                        "retrieval",
                        "retrieval_failed",
                        msg,
                    )
                ],
            }

        next_route = route_after_retrieval(
            {**state, "retrieved_docs": docs, "node_status": {**(state.get("node_status") or {}), "retrieval": "ok"}}
        )
        to_node = "research" if next_route == "research" else "tools"
        result: dict[str, Any] = {
            "retrieved_docs": docs,
            "current_node": "retrieval",
            **update_node_status(state, "retrieval", "ok" if docs else "degraded"),
            **record_handoff(
                state,
                from_node="retrieval",
                to_node=to_node,  # type: ignore[arg-type]
                summary=f"Retrieved {len(docs)} chunks; next={next_route}.",
                doc_count=len(docs),
            ),
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
        if next_route == "research":
            result.update(build_retrieval_escalation({**state, **result}))
        return result

    async def tools(self, state: AgentState) -> dict[str, Any]:
        return await run_tool_node(state, self._tool_node)

    async def research(self, state: AgentState) -> dict[str, Any]:
        question = state["user_question"]
        try:
            rlm_result = await run_rlm_pipeline(
                question=question,
                state=state,
                retriever=self._retriever,
            )
        except Exception as exc:
            logger.exception("Research node failed")
            return {
                "retrieved_docs": [],
                "research_notes": "",
                "current_node": "research",
                **update_node_status(state, "research", "failed", detail=str(exc)[:80]),
                **record_failure(
                    state,
                    source_node="research",
                    error_type=type(exc).__name__,
                    message=str(exc)[:200],
                ),
                **record_handoff(
                    state,
                    from_node="research",
                    to_node="tools",
                    summary="RLM pipeline failed; continuing with empty research context.",
                ),
                "agent_events": [
                    make_event("research", "research_failed", f"RLM failed: {exc}"),
                ],
            }

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
        doc_count = len(rlm_result.retrieved_docs)
        status = "ok" if doc_count else "degraded"

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
            **update_node_status(state, "research", status),
            **record_handoff(
                state,
                from_node="research",
                to_node="tools",
                summary=f"RLM complete: {len(batch_summaries)} batches, {doc_count} unique chunks.",
                batches=len(batch_summaries),
            ),
            "agent_events": rlm_result.agent_events,
        }

    async def response(self, state: AgentState) -> dict[str, Any]:
        docs = state.get("retrieved_docs") or []
        context = _format_context(docs)
        question = state["user_question"]
        stream_tokens = bool(state.get("stream_tokens"))
        writer = _get_stream_writer() if stream_tokens else None

        try:
            if writer is not None:
                answer = await self._generate_answer_stream(question, context, state, writer)
            else:
                answer = await self._generate_answer(question, context, state)
            llm_available = True
        except (LLMError, Exception):
            logger.exception("Response node LLM failed")
            answer = llm_unavailable_answer(question, docs)
            llm_available = False
            failure_patch = record_failure(
                state,
                source_node="response",
                error_type="llm_unavailable",
                message="Answer synthesis unavailable",
                recoverable=True,
            )
            if writer is not None:
                writer({"type": "token", "content": answer})
        else:
            failure_patch = {}

        return {
            "final_answer": answer,
            "llm_available": llm_available,
            "current_node": "response",
            "retry_response": False,
            **update_node_status(
                state,
                "response",
                "ok" if llm_available else "degraded",
            ),
            **failure_patch,
            **record_handoff(
                state,
                from_node="response",
                to_node="validate",
                summary="Draft answer ready for guardrail validation.",
                llm_available=llm_available,
            ),
            "agent_events": [
                make_event(
                    "response",
                    "answer_generated",
                    "Draft answer composed from retrieved context",
                    llm_available=llm_available,
                    context_chunks=len(docs),
                    correction=bool(state.get("retry_response")),
                )
            ],
        }

    async def validate(self, state: AgentState) -> dict[str, Any]:
        answer = state.get("final_answer") or ""
        docs = state.get("retrieved_docs") or []
        issues = validate_answer_guardrails(
            answer,
            docs,
            user_role=state.get("user_role", "viewer"),
            tool_calls=state.get("tool_calls"),
        )
        passed = len(issues) == 0
        attempts = int(state.get("correction_attempts") or 0)
        will_retry = (
            not passed
            and attempts < 1
            and bool(docs)
            and state.get("llm_available", True)
        )

        final_answer = answer
        if not passed and docs and not will_retry:
            final_answer = (
                f"{answer}\n\n"
                f"[Validation note: {'; '.join(issues)}]"
            )

        result: dict[str, Any] = {
            "final_answer": final_answer,
            "validation_passed": passed,
            "validation_issues": issues,
            "retry_response": will_retry,
            "current_node": "validate",
            **update_node_status(state, "validate", "ok" if passed else "degraded"),
            "agent_events": [
                make_event(
                    "validate",
                    "validation_complete",
                    "Validation passed" if passed else "Validation flagged issues",
                    passed=passed,
                    issues=issues,
                    will_retry=will_retry,
                )
            ],
        }
        if will_retry:
            result.update(build_validation_correction(state))
        elif not passed:
            result.update(
                record_handoff(
                    state,
                    from_node="validate",
                    to_node="validate",
                    summary="Validation failed; no further correction attempts.",
                    issues=issues,
                )
            )
        return result

    async def _decide_route(
        self,
        question: str,
        state: AgentState,
    ) -> tuple[Route, str]:
        heuristic_route, heuristic_plan = _heuristic_route(question)
        llm = get_chat_llm()
        settings = get_settings()
        run_config = build_run_config(
            run_name="supervisor_routing",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "supervisor"],
        )

        try:
            response = await invoke_llm(
                llm,
                [
                    SystemMessage(content=SUPERVISOR_PROMPT),
                    HumanMessage(content=_supervisor_prompt(question, state)),
                ],
                config=run_config,
                timeout_seconds=settings.llm_timeout_seconds,
            )
            parsed = _parse_json(str(response.content))
            route = parsed.get("route", heuristic_route)
            plan = parsed.get("plan", heuristic_plan)
            if route not in {"retrieval", "research"}:
                route = heuristic_route
            route, plan = _apply_role_route_policy(route, plan, state)
            return route, plan
        except Exception:
            logger.warning("Supervisor LLM routing failed; using heuristics")
            route, plan = heuristic_route, heuristic_plan
            route, plan = _apply_role_route_policy(route, plan, state)
            return route, plan

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
        settings = get_settings()
        run_config = build_run_config(
            run_name="agent_response",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "response"],
        )
        messages = _build_response_messages(question, context, state)

        response = await invoke_llm(
            llm,
            messages,
            config=run_config,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        content = str(response.content).strip()
        if not content:
            raise RuntimeError("Empty LLM response")
        return content

    async def _generate_answer_stream(
        self,
        question: str,
        context: str,
        state: AgentState,
        writer,
    ) -> str:
        llm = get_chat_llm()
        settings = get_settings()
        run_config = build_run_config(
            run_name="agent_response",
            request_id=state.get("request_id"),
            session_id=state.get("session_id"),
            user_role=state.get("user_role"),
            tags=["agent", "response", "stream"],
        )
        messages = _build_response_messages(question, context, state)
        parts: list[str] = []
        async for token in stream_llm(
            llm,
            messages,
            config=run_config,
            timeout_seconds=settings.llm_timeout_seconds,
        ):
            parts.append(token)
            writer({"type": "token", "content": token})
        content = "".join(parts).strip()
        if not content:
            raise RuntimeError("Empty LLM stream response")
        return content


def _get_stream_writer():
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        return None


def _build_response_messages(
    question: str,
    context: str,
    state: AgentState,
) -> list[SystemMessage | HumanMessage]:
    research_notes = state.get("research_notes")
    batch_summaries = state.get("batch_summaries") or []
    extra_parts = []

    degraded = format_degraded_banner(state)
    if degraded:
        extra_parts.append(degraded)
    handoffs = format_handoffs_for_prompt(state)
    if handoffs:
        extra_parts.append(handoffs)

    if state.get("retry_response") or (state.get("validation_issues") and state.get("correction_attempts")):
        issues = state.get("validation_issues") or []
        extra_parts.append(
            "Previous answer failed validation. Address these issues:\n"
            + "\n".join(f"- {issue}" for issue in issues)
        )

    if research_notes:
        extra_parts.append(f"Research notes:\n{research_notes}")
    if batch_summaries:
        partials = "\n".join(
            f"- [{b.get('batch_id')}] {b.get('summary', '')[:300]}"
            for b in batch_summaries
        )
        extra_parts.append(f"Batch partial summaries:\n{partials}")
    analysis_results = sanitize_tool_output_for_prompt(state.get("analysis_results"))
    if analysis_results:
        extra_parts.append(f"Tool analysis results:\n{analysis_results}")
    mcp_results = sanitize_tool_output_for_prompt(state.get("mcp_results"))
    if mcp_results:
        extra_parts.append(f"MCP enterprise data:\n{mcp_results}")
    extra = f"\n\n{chr(10).join(extra_parts)}" if extra_parts else ""
    history_block = format_history_for_prompt(state.get("chat_history") or [])
    history_section = f"\n\nConversation history:\n{history_block}" if history_block else ""

    return [
        SystemMessage(content=RESPONSE_PROMPT),
        HumanMessage(
            content=(
                f"Context:\n{context}{extra}{history_section}\n\n"
                f"Question: {question}\n\nAnswer:"
            )
        ),
    ]


def _apply_role_route_policy(
    route: Route,
    plan: str,
    state: AgentState,
) -> tuple[Route, str]:
    role = state.get("user_role", "viewer")
    if route == "research" and not can_use_research_route(role):
        return "retrieval", f"{plan} (downgraded: {role} cannot use research route)"
    return route, plan


def _supervisor_prompt(question: str, state: AgentState) -> str:
    history = format_history_for_prompt(state.get("chat_history") or [], max_turns=3)
    if history:
        return f"Conversation so far:\n{history}\n\nCurrent question: {question}"
    return f"Question: {question}"


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
        source = doc.get("source_file", "unknown")
        title = doc.get("title", "")
        body = doc.get("text") or doc.get("text_preview", "")
        wrapped = wrap_untrusted_document(body, source_file=source, title=title)
        blocks.append(f"[Document {i}]\n{wrapped}")
    return "\n\n".join(blocks)
