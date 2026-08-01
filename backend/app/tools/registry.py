"""Tool registry and LangGraph ToolNode factory."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from backend.app.retrieval import HybridRetriever
from backend.app.tools.knowledge_search import create_knowledge_search_tool
from backend.app.tools.python_analysis import create_python_analysis_tool

ANALYSIS_QUERY_PATTERNS = (
    r"\bhow many\b",
    r"\bcount\b",
    r"\bbreakdown\b",
    r"\bdistribution\b",
    r"\bgroup by\b",
    r"\bstatistics\b",
    r"\bunique sources\b",
    r"\bscore summary\b",
)


def build_tools(retriever: HybridRetriever) -> list:
    """Return LangChain tools registered with the agent."""
    return [
        create_knowledge_search_tool(retriever),
        create_python_analysis_tool(),
    ]


def build_tool_node(retriever: HybridRetriever) -> ToolNode:
    return ToolNode(build_tools(retriever))


def needs_analysis(question: str) -> bool:
    lowered = question.lower()
    return any(re.search(pattern, lowered) for pattern in ANALYSIS_QUERY_PATTERNS)


def infer_analysis_operation(question: str) -> tuple[str, str | None]:
    lowered = question.lower()
    if "namespace" in lowered or "folder" in lowered:
        return "group_by_namespace", None
    if "score" in lowered or "relevance" in lowered:
        return "score_summary", None
    if "unique" in lowered or "sources" in lowered or "documents" in lowered:
        return "list_unique_sources", None
    if "incident" in lowered:
        return "count_by_field", "document_type"
    if "department" in lowered:
        return "count_by_field", "department"
    return "count_by_field", "document_type"


def plan_tool_calls(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Plan tool invocations from agent state (heuristic planner for ToolNode)."""
    calls: list[dict[str, Any]] = []
    docs = state.get("retrieved_docs") or []
    question = state.get("user_question", "")

    if docs and needs_analysis(question):
        operation, field = infer_analysis_operation(question)
        args: dict[str, Any] = {
            "records_json": json.dumps(docs),
            "operation": operation,
        }
        if field:
            args["field"] = field
        calls.append(
            {
                "name": "python_analysis",
                "args": args,
                "id": f"call_analysis_{uuid.uuid4().hex[:8]}",
            }
        )

    return calls


async def run_tool_node(
    state: dict[str, Any],
    tool_node: ToolNode,
    *,
    inject_user_role: bool = True,
) -> dict[str, Any]:
    """
    Execute planned tools via LangGraph ToolNode and collect results into state.

    Injects user_role into knowledge_search calls when missing.
    """
    from backend.app.agents.events import make_event

    planned = plan_tool_calls(state)
    if not planned:
        return {
            "current_node": "tools",
            "agent_events": [
                make_event(
                    "tools",
                    "tools_skipped",
                    "No tools required for this query",
                )
            ],
        }

    tool_calls_payload = []
    for call in planned:
        args = dict(call["args"])
        if call["name"] == "knowledge_search" and inject_user_role:
            args.setdefault("user_role", state.get("user_role", "viewer"))
        tool_calls_payload.append(
            {
                "name": call["name"],
                "args": args,
                "id": call["id"],
                "type": "tool_call",
            }
        )

    ai_message = AIMessage(content="", tool_calls=tool_calls_payload)
    tool_result = await tool_node.ainvoke({"messages": [ai_message]})

    analysis_results: list[str] = []
    tool_calls_log: list[dict[str, Any]] = []
    events = [
        make_event(
            "tools",
            "tools_started",
            f"Executing {len(planned)} tool call(s)",
            tools=[c["name"] for c in planned],
        )
    ]

    for message in tool_result.get("messages", []):
        if isinstance(message, ToolMessage):
            analysis_results.append(message.content)
            tool_calls_log.append(
                {
                    "tool": message.name,
                    "tool_call_id": message.tool_call_id,
                    "output_preview": str(message.content)[:300],
                }
            )
            events.append(
                make_event(
                    "tools",
                    "tool_complete",
                    f"Tool {message.name} completed",
                    tool=message.name,
                )
            )

    combined_analysis = "\n".join(analysis_results)

    return {
        "messages": tool_result.get("messages", []),
        "analysis_results": combined_analysis,
        "tool_calls": tool_calls_log,
        "current_node": "tools",
        "agent_events": events,
    }
