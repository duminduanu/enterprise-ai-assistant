"""Tool registry and LangGraph ToolNode factory."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from backend.app.retrieval import HybridRetriever
from backend.app.security.rbac import can_use_tool
from backend.app.security.tool_validation import validate_tool_call
from backend.app.tools.knowledge_search import create_knowledge_search_tool
from backend.app.tools.mcp_tools import create_mcp_tools
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

MCP_SERVICE_PATTERNS = (
    r"\bwho owns\b",
    r"\bowner of\b",
    r"\bservice catalog\b",
    r"\bon-?call\b",
    r"\bwhich team owns\b",
)

MCP_EMPLOYEE_PATTERNS = (
    r"\bemployee directory\b",
    r"\bfind employee\b",
    r"\bcontact for\b",
    r"\bwho is\b.*\b(engineer|manager|director)\b",
)

MCP_INCIDENT_PATTERNS = (
    r"\binc-\d{4}-\d+\b",
    r"\bopen incident\b",
    r"\bincident record\b",
    r"\bincident status\b",
)

MCP_ALLOWED_ROLES = frozenset({"analyst", "admin"})


def build_tools(retriever: HybridRetriever) -> list:
    """Return LangChain tools registered with the agent."""
    return [
        create_knowledge_search_tool(retriever),
        create_python_analysis_tool(),
        *create_mcp_tools(),
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


def needs_mcp_lookup(question: str, user_role: str) -> bool:
    if user_role not in MCP_ALLOWED_ROLES:
        return False
    lowered = question.lower()
    patterns = MCP_SERVICE_PATTERNS + MCP_EMPLOYEE_PATTERNS + MCP_INCIDENT_PATTERNS
    return any(re.search(pattern, lowered) for pattern in patterns)


def infer_mcp_tool(question: str) -> tuple[str, str]:
    lowered = question.lower()

    incident_match = re.search(r"\binc-\d{4}-\d+\b", question, re.IGNORECASE)
    if incident_match or any(re.search(p, lowered) for p in MCP_INCIDENT_PATTERNS):
        query = incident_match.group(0) if incident_match else _extract_search_terms(question)
        return "lookup_incident", query

    if any(re.search(p, lowered) for p in MCP_EMPLOYEE_PATTERNS):
        return "lookup_employee", _extract_search_terms(question)

    if any(re.search(p, lowered) for p in MCP_SERVICE_PATTERNS):
        return "lookup_service", _extract_service_query(question)

    return "lookup_service", _extract_search_terms(question)


def _extract_service_query(question: str) -> str:
    cleaned = re.sub(r"(?i)^who owns (the )?", "", question.strip())
    cleaned = re.sub(r"(?i)\bservice\??$", "", cleaned).strip(" ?.")
    return cleaned or question.strip()


def _extract_search_terms(question: str) -> str:
    cleaned = re.sub(
        r"(?i)^(who owns|who is|find|lookup|search for|contact for)\s+(the )?",
        "",
        question.strip(),
    )
    cleaned = cleaned.rstrip("?.")
    return cleaned or question.strip()


def plan_tool_calls(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Plan tool invocations from agent state (heuristic planner for ToolNode)."""
    calls: list[dict[str, Any]] = []
    docs = state.get("retrieved_docs") or []
    question = state.get("user_question", "")
    user_role = state.get("user_role", "viewer")

    if needs_mcp_lookup(question, user_role) and can_use_tool(user_role, "lookup_service"):
        tool_name, query = infer_mcp_tool(question)
        calls.append(
            {
                "name": tool_name,
                "args": {"query": query},
                "id": f"call_mcp_{uuid.uuid4().hex[:8]}",
            }
        )

    if (
        docs
        and needs_analysis(question)
        and can_use_tool(user_role, "python_analysis")
    ):
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
    events: list[dict[str, Any]] = []
    for call in planned:
        if not can_use_tool(state.get("user_role", "viewer"), call["name"]):
            events.append(
                make_event(
                    "tools",
                    "tool_denied",
                    f"Role cannot invoke {call['name']}",
                    tool=call["name"],
                    role=state.get("user_role"),
                )
            )
            continue
        args = dict(call["args"])
        ok, err = validate_tool_call(call["name"], args)
        if not ok:
            events.append(
                make_event(
                    "tools",
                    "tool_invalid",
                    f"Rejected {call['name']}: {err}",
                    tool=call["name"],
                )
            )
            continue
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

    if not tool_calls_payload:
        return {
            "current_node": "tools",
            "agent_events": events
            + [
                make_event(
                    "tools",
                    "tools_skipped",
                    "No permitted tools for this role/query",
                )
            ],
        }

    events.append(
        make_event(
            "tools",
            "tools_started",
            f"Executing {len(tool_calls_payload)} tool call(s)",
            tools=[c["name"] for c in tool_calls_payload],
        )
    )

    ai_message = AIMessage(content="", tool_calls=tool_calls_payload)
    tool_result = await tool_node.ainvoke({"messages": [ai_message]})

    analysis_results: list[str] = []
    mcp_results: list[str] = []
    tool_calls_log: list[dict[str, Any]] = []

    for message in tool_result.get("messages", []):
        if isinstance(message, ToolMessage):
            content = str(message.content)
            if message.name and message.name.startswith("lookup_"):
                mcp_results.append(content)
            else:
                analysis_results.append(content)
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
    combined_mcp = "\n".join(mcp_results)

    return {
        "messages": tool_result.get("messages", []),
        "analysis_results": combined_analysis,
        "mcp_results": combined_mcp,
        "tool_calls": tool_calls_log,
        "current_node": "tools",
        "agent_events": events,
    }
