"""LangGraph agent state definition."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

Route = Literal["retrieval", "research"]


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph agent nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_question: str
    user_role: str
    session_id: str
    request_id: str
    department: str | None
    document_type: str | None
    chat_history: list[dict[str, str]]

    plan: str
    route: Route
    retrieved_docs: list[dict[str, Any]]
    research_notes: str
    research_plan: dict[str, Any]
    batch_summaries: list[dict[str, Any]]
    sub_queries: list[str]

    analysis_results: str
    mcp_results: str
    tool_calls: Annotated[list[dict[str, Any]], operator.add]
    agent_events: Annotated[list[dict[str, Any]], operator.add]
    current_node: str

    final_answer: str
    validation_passed: bool
    validation_issues: list[str]
    llm_available: bool
    stream_tokens: bool
    retry_response: bool

    # Multi-agent collaboration (Step S bonus)
    node_status: dict[str, str]
    failure_chain: Annotated[list[dict[str, Any]], operator.add]
    handoff_notes: Annotated[list[dict[str, Any]], operator.add]
    degraded_mode: bool
    degraded_reasons: Annotated[list[str], operator.add]
    retrieval_escalated: bool
    correction_attempts: int
    butterfly_impact: dict[str, Any]
