"""Stream LangGraph agent execution with SSE-friendly events."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langsmith import traceable

from backend.app.agents.collaboration import initial_collaboration_state
from backend.app.agents.events import make_event
from backend.app.agents.graph import get_compiled_agent_graph
from backend.app.core.config import get_settings
from backend.app.core.fallbacks import agent_timeout_answer
from backend.app.memory.session_store import contextualize_question, get_session_store
from backend.app.observability.langsmith_config import build_run_config

logger = logging.getLogger(__name__)


def _history_to_messages(history: list[dict[str, str]]) -> list[HumanMessage | AIMessage]:
    messages: list[HumanMessage | AIMessage] = []
    for turn in history:
        content = turn.get("content", "").strip()
        if not content:
            continue
        if turn.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    return messages


def _merge_state(accumulated: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(accumulated)
    append_keys = {
        "agent_events",
        "tool_calls",
        "failure_chain",
        "handoff_notes",
        "degraded_reasons",
    }
    for key, value in update.items():
        if key in append_keys and isinstance(value, list):
            merged[key] = list(merged.get(key) or []) + value
        elif key == "node_status" and isinstance(value, dict):
            merged[key] = {**(merged.get(key) or {}), **value}
        else:
            merged[key] = value
    return merged


@traceable(name="langgraph_agent_stream", run_type="chain")
async def stream_agent(
    *,
    message: str,
    user_role: str,
    session_id: str,
    request_id: str,
    department: str | None = None,
    document_type: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yield streaming payloads while the LangGraph agent runs.

    Yields dicts with ``type`` in ``node``, ``agent_event``, ``token``, ``done``.
    """
    store = get_session_store()
    history = await store.get_history(session_id)
    contextual_question = contextualize_question(message, history)

    prior_messages = _history_to_messages(history)
    current_messages = prior_messages + [HumanMessage(content=message)]

    graph = get_compiled_agent_graph()
    initial_state: dict[str, Any] = {
        "messages": current_messages,
        "user_question": message,
        "user_role": user_role,
        "session_id": session_id,
        "request_id": request_id,
        "department": department,
        "document_type": document_type,
        "chat_history": history,
        "retrieved_docs": [],
        "tool_calls": [],
        "agent_events": [],
        "validation_issues": [],
        "stream_tokens": True,
        **initial_collaboration_state(),
    }

    config = build_run_config(
        run_name="enterprise_agent_stream",
        request_id=request_id,
        session_id=session_id,
        user_role=user_role,
        tags=["langgraph", "multi-agent", "stream"],
        metadata={
            "question_preview": message[:120],
            "history_turns": len(history),
            "contextualized": contextual_question != message,
        },
    )

    settings = get_settings()
    accumulated: dict[str, Any] = dict(initial_state)
    timed_out = False

    try:
        async with asyncio.timeout(settings.agent_timeout_seconds):
            async for mode, chunk in graph.astream(
                initial_state,
                config=config,
                stream_mode=["updates", "custom"],
            ):
                if mode == "updates":
                    for node_name, update in chunk.items():
                        accumulated = _merge_state(accumulated, update)
                        yield {
                            "type": "node",
                            "node": node_name,
                            "status": "complete",
                            "current_node": update.get("current_node", node_name),
                            "route": update.get("route"),
                        }
                        for event in update.get("agent_events") or []:
                            yield {"type": "agent_event", "event": event}
                elif mode == "custom" and isinstance(chunk, dict):
                    if chunk.get("type") == "token":
                        yield {"type": "token", "content": chunk.get("content", "")}
    except TimeoutError:
        timed_out = True
        logger.warning("Streaming agent timed out request_id=%s session_id=%s", request_id, session_id)
        timeout_event = make_event(
            "system",
            "agent_timeout",
            agent_timeout_answer(),
            request_id=request_id,
        )
        accumulated = _merge_state(
            accumulated,
            {
                "final_answer": agent_timeout_answer(),
                "validation_passed": False,
                "current_node": "timeout",
                "agent_events": [timeout_event],
            },
        )
        yield {"type": "agent_event", "event": timeout_event}
        yield {"type": "token", "content": agent_timeout_answer()}
    except Exception as exc:
        logger.exception("Streaming agent failed request_id=%s", request_id)
        error_event = make_event(
            "system",
            "agent_stream_error",
            str(exc)[:200],
            request_id=request_id,
        )
        accumulated = _merge_state(
            accumulated,
            {
                "final_answer": agent_timeout_answer(),
                "validation_passed": False,
                "current_node": "error",
                "agent_events": [error_event],
            },
        )
        yield {"type": "agent_event", "event": error_event}

    if not timed_out and not accumulated.get("final_answer"):
        accumulated["final_answer"] = ""

    answer = accumulated.get("final_answer") or ""
    if answer:
        await store.append_turn(session_id, "user", message)
        await store.append_turn(session_id, "assistant", answer)

    accumulated["chat_history"] = await store.get_history(session_id)
    accumulated["history_turns"] = len(history)
    yield {"type": "done", "result": accumulated}
