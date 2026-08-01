"""Multi-agent collaboration: shared state, handoffs, failure chains, and cascade containment.

Agents do not message each other directly. They collaborate through ``AgentState``:
each node reads upstream fields, writes partial updates, and records handoffs so
downstream agents can adapt when earlier steps degrade (the "butterfly effect").
"""

from __future__ import annotations

from typing import Any, Literal

from backend.app.agents.events import make_event
from backend.app.agents.state import AgentState
from backend.app.security.rbac import can_use_research_route

NodeName = Literal[
    "supervisor",
    "retrieval",
    "research",
    "tools",
    "response",
    "validate",
]
NodeStatus = Literal["ok", "degraded", "failed", "skipped"]

# Downstream nodes that may be impacted when an upstream node fails.
CASCADE_GRAPH: dict[str, list[str]] = {
    "supervisor": ["retrieval", "research", "response"],
    "retrieval": ["tools", "response", "validate"],
    "research": ["tools", "response", "validate"],
    "tools": ["response", "validate"],
    "response": ["validate"],
    "validate": [],
}

MAX_CORRECTION_ATTEMPTS = 1


def update_node_status(
    state: AgentState,
    node: NodeName,
    status: NodeStatus,
    *,
    detail: str = "",
) -> dict[str, Any]:
    """Merge node outcome into shared status map."""
    current = dict(state.get("node_status") or {})
    current[node] = status
    payload: dict[str, Any] = {"node_status": current, "current_node": node}
    if detail:
        payload["agent_events"] = [
            make_event(
                node,
                "node_status",
                f"{node} → {status}" + (f": {detail}" if detail else ""),
                status=status,
            )
        ]
    return payload


def record_failure(
    state: AgentState,
    *,
    source_node: NodeName,
    error_type: str,
    message: str,
    recoverable: bool = True,
) -> dict[str, Any]:
    """Append to the failure chain and mark degraded mode for downstream awareness."""
    downstream = CASCADE_GRAPH.get(source_node, [])
    record = {
        "source": source_node,
        "error_type": error_type,
        "message": message[:300],
        "recoverable": recoverable,
        "downstream_at_risk": downstream,
    }
    impact = assess_butterfly_effect(state, new_failure=record)
    events = [
        make_event(
            "collaboration",
            "failure_recorded",
            f"{source_node} failure may affect {', '.join(downstream) or 'none'}",
            failure=record,
            impact=impact,
        )
    ]
    if impact.get("severity") in {"high", "critical"}:
        events.append(
            make_event(
                "collaboration",
                "butterfly_effect",
                impact.get("summary", "Upstream failure may cascade"),
                containment=impact.get("containment", []),
            )
        )
    return {
        "failure_chain": [record],
        "degraded_mode": True,
        "degraded_reasons": [f"{source_node}: {message[:120]}"],
        "butterfly_impact": impact,
        "agent_events": events,
    }


def record_handoff(
    state: AgentState,
    *,
    from_node: NodeName,
    to_node: NodeName,
    summary: str,
    **context: Any,
) -> dict[str, Any]:
    """Structured agent-to-agent handoff stored in shared state (not chat messages)."""
    note = {
        "from": from_node,
        "to": to_node,
        "summary": summary[:500],
        "context": context,
    }
    return {
        "handoff_notes": [note],
        "agent_events": [
            make_event(
                "collaboration",
                "handoff",
                f"{from_node} → {to_node}: {summary[:160]}",
                handoff=note,
            )
        ],
    }


def assess_butterfly_effect(
    state: AgentState,
    *,
    new_failure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Estimate how upstream failures propagate (butterfly effect).

    Returns severity, affected nodes, and recommended containment actions.
    """
    chain = list(state.get("failure_chain") or [])
    if new_failure:
        chain = chain + [new_failure]

    if not chain:
        return {"severity": "none", "summary": "No failures recorded", "containment": []}

    sources = {f.get("source") for f in chain}
    at_risk: set[str] = set()
    for failure in chain:
        at_risk.update(failure.get("downstream_at_risk") or [])

    retrieval_failed = "retrieval" in sources
    tools_failed = "tools" in sources
    llm_failed = "response" in sources or any(
        f.get("error_type") == "llm_unavailable" for f in chain
    )
    no_docs = not (state.get("retrieved_docs") or [])

    containment: list[str] = []
    severity = "low"

    if retrieval_failed and no_docs:
        severity = "high"
        containment.extend(
            [
                "escalate_to_research_if_permitted",
                "skip_tools_without_context",
                "response_use_retrieval_fallback",
            ]
        )
    if tools_failed:
        severity = max(severity, "medium", key=_severity_rank)
        containment.append("sanitize_tool_errors_in_prompt")
    if llm_failed:
        severity = "critical"
        containment.append("retrieval_only_answer")
    if len(chain) >= 2:
        severity = max(severity, "high", key=_severity_rank)
        containment.append("surface_degraded_mode_to_user")

    summary_parts = [f"{len(chain)} upstream failure(s)"]
    if no_docs:
        summary_parts.append("empty context")
    if llm_failed:
        summary_parts.append("LLM synthesis at risk")

    return {
        "severity": severity,
        "failure_count": len(chain),
        "sources": sorted(sources),
        "nodes_at_risk": sorted(at_risk),
        "summary": "; ".join(summary_parts),
        "containment": list(dict.fromkeys(containment)),
    }


def route_after_retrieval(state: AgentState) -> str:
    """
    Failure-aware routing: empty/failed retrieval may escalate to research once.

    Prevents a silent butterfly effect where tools/response run with no context.
    """
    docs = state.get("retrieved_docs") or []
    node_status = (state.get("node_status") or {}).get("retrieval", "ok")
    role = state.get("user_role", "viewer")

    if (
        not docs
        and not state.get("retrieval_escalated")
        and state.get("route") == "retrieval"
        and can_use_research_route(role)
        and node_status in {"failed", "ok"}
    ):
        return "research"

    return "tools"


def build_retrieval_escalation(state: AgentState) -> dict[str, Any]:
    """State patch when retrieval escalates to research."""
    impact = assess_butterfly_effect(state)
    return {
        "retrieval_escalated": True,
        "route": "research",
        "plan": (state.get("plan") or "") + " (escalated: retrieval returned no context)",
        **record_handoff(
            state,
            from_node="retrieval",
            to_node="research",
            summary="Retrieval produced no usable documents; escalating to RLM research pipeline.",
            doc_count=0,
        ),
        **record_failure(
            state,
            source_node="retrieval",
            error_type="empty_context",
            message="No documents retrieved; escalating to research agent",
            recoverable=True,
        ),
        "agent_events": [
            make_event(
                "collaboration",
                "retrieval_escalation",
                "Routing to research after empty retrieval",
                butterfly_impact=impact,
            )
        ],
    }


def route_after_validate(state: AgentState) -> str:
    """Self-correction loop: validation failure may send work back to response once."""
    if state.get("validation_passed"):
        return "__end__"
    if state.get("retry_response"):
        return "response"
    return "__end__"


def build_validation_correction(state: AgentState) -> dict[str, Any]:
    """Prepare state for a validation-driven response retry."""
    issues = state.get("validation_issues") or []
    attempts = int(state.get("correction_attempts") or 0)
    return {
        "correction_attempts": attempts + 1,
        **record_handoff(
            state,
            from_node="validate",
            to_node="response",
            summary="Validation flagged issues; requesting corrected answer.",
            issues=issues,
            attempt=attempts + 1,
        ),
        "agent_events": [
            make_event(
                "collaboration",
                "validation_correction",
                f"Re-running response (attempt {attempts + 1})",
                issues=issues,
            )
        ],
    }


def should_skip_tools(state: AgentState) -> tuple[bool, str]:
    """
    Circuit breaker: skip tools when upstream context is missing or retrieval failed.

    Avoids the butterfly effect of running MCP/analysis on empty or error state.
    """
    docs = state.get("retrieved_docs") or []
    node_status = state.get("node_status") or {}
    impact = state.get("butterfly_impact") or assess_butterfly_effect(state)

    if "skip_tools_without_context" in (impact.get("containment") or []):
        if not docs:
            return True, "Skipping tools: no retrieval context (cascade containment)"

    if node_status.get("retrieval") == "failed" and not docs:
        return True, "Skipping tools: retrieval failed with no fallback documents"

    return False, ""


def sanitize_tool_output_for_prompt(text: str | None) -> str:
    """Keep tool error payloads out of the synthesis prompt as if they were results."""
    if not text or not text.strip():
        return ""
    lowered = text.strip().lower()
    if lowered.startswith('{"error"') or '"fallback": "continue_without' in lowered:
        return ""
    return text.strip()


def format_handoffs_for_prompt(state: AgentState) -> str:
    """Render agent handoff notes for the response synthesizer."""
    notes = state.get("handoff_notes") or []
    if not notes:
        return ""
    lines = ["Agent handoffs (collaboration trace):"]
    for note in notes[-5:]:
        lines.append(
            f"- [{note.get('from')} → {note.get('to')}] {note.get('summary', '')}"
        )
    return "\n".join(lines)


def format_degraded_banner(state: AgentState) -> str:
    """Brief instruction when operating in degraded multi-agent mode."""
    if not state.get("degraded_mode"):
        return ""
    reasons = state.get("degraded_reasons") or []
    impact = state.get("butterfly_impact") or {}
    reason_text = "; ".join(reasons[:3]) if reasons else "upstream agent degradation"
    return (
        f"[Degraded mode: {reason_text}. "
        f"Severity: {impact.get('severity', 'unknown')}. "
        "Answer conservatively; cite only provided context.]"
    )


def initial_collaboration_state() -> dict[str, Any]:
    """Default collaboration fields for graph entry."""
    return {
        "node_status": {},
        "failure_chain": [],
        "handoff_notes": [],
        "degraded_mode": False,
        "degraded_reasons": [],
        "retrieval_escalated": False,
        "correction_attempts": 0,
        "butterfly_impact": {"severity": "none", "summary": "No failures recorded", "containment": []},
    }


def _severity_rank(level: str) -> int:
    return {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(level, 0)
