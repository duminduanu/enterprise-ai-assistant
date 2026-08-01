#!/usr/bin/env python3
"""Test multi-agent collaboration: state, handoffs, failure chains, cascade containment."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.agents.collaboration import (  # noqa: E402
    assess_butterfly_effect,
    build_retrieval_escalation,
    initial_collaboration_state,
    record_failure,
    route_after_retrieval,
    route_after_validate,
    sanitize_tool_output_for_prompt,
    should_skip_tools,
)
from backend.app.agents.graph import build_agent_graph  # noqa: E402
from backend.app.retrieval.hybrid_search import HybridRetriever  # noqa: E402


def test_initial_collaboration_state() -> None:
    state = initial_collaboration_state()
    assert state["degraded_mode"] is False
    assert state["failure_chain"] == []
    assert state["correction_attempts"] == 0
    print("initial collaboration state: OK")


def test_butterfly_effect_assessment() -> None:
    base = {
        **initial_collaboration_state(),
        "retrieved_docs": [],
        "user_role": "analyst",
        "route": "retrieval",
    }
    patch_state = {
        **base,
        **record_failure(
            base,
            source_node="retrieval",
            error_type="ToolTimeoutError",
            message="search timed out",
        ),
    }
    impact = assess_butterfly_effect(patch_state)
    assert impact["severity"] in {"high", "critical"}
    assert "tools" in impact.get("nodes_at_risk", [])
    assert "skip_tools_without_context" in impact.get("containment", [])
    print(f"butterfly effect assessment ({impact['severity']}): OK")


def test_retrieval_escalation_routing() -> None:
    state = {
        **initial_collaboration_state(),
        "retrieved_docs": [],
        "route": "retrieval",
        "user_role": "analyst",
        "node_status": {"retrieval": "ok"},
    }
    assert route_after_retrieval(state) == "research"
    escalated = {**state, **build_retrieval_escalation(state)}
    assert escalated["retrieval_escalated"] is True
    assert any(n["from"] == "retrieval" for n in escalated["handoff_notes"])
    assert route_after_retrieval(escalated) == "tools"
    print("retrieval -> research escalation: OK")


def test_tools_circuit_breaker() -> None:
    state = {
        **initial_collaboration_state(),
        "retrieved_docs": [],
        **record_failure(
            {**initial_collaboration_state(), "retrieved_docs": []},
            source_node="retrieval",
            error_type="empty_context",
            message="no docs",
        ),
    }
    skip, reason = should_skip_tools(state)
    assert skip is True
    assert "context" in reason.lower()
    print(f"tools circuit breaker ({reason[:50]}…): OK")


def test_sanitize_tool_errors() -> None:
    raw = '{"error": "Tool failed", "fallback": "continue_without_tool"}'
    assert sanitize_tool_output_for_prompt(raw) == ""
    assert sanitize_tool_output_for_prompt("count=42 by department") == "count=42 by department"
    print("sanitize tool error payloads: OK")


def test_validation_correction_routing() -> None:
    state = {
        **initial_collaboration_state(),
        "validation_passed": False,
        "retry_response": True,
    }
    assert route_after_validate(state) == "response"
    state["retry_response"] = False
    assert route_after_validate(state) == "__end__"
    print("validation self-correction routing: OK")


def test_graph_compiles_with_collaboration_edges() -> None:
    graph = build_agent_graph(HybridRetriever())
    assert graph is not None
    print("graph compile with collaboration edges: OK")


async def test_agent_run_records_handoffs() -> None:
    from backend.app.agents.runner import run_agent

    result = await run_agent(
        message="What is the password reset policy?",
        user_role="analyst",
        session_id="collab-test",
        request_id="collab-req",
    )
    handoffs = result.get("handoff_notes") or []
    assert handoffs, "expected agent handoff notes in shared state"
    assert result.get("node_status"), "expected per-node status map"
    print(f"live agent handoffs ({len(handoffs)}): OK")


async def test_retrieval_failure_cascade() -> None:
    """Simulate retrieval failure output merged into shared state."""
    state_in = {
        "user_question": "What is the password policy?",
        "user_role": "analyst",
        **initial_collaboration_state(),
    }
    retrieval_out = {
        "retrieved_docs": [],
        **record_failure(
            state_in,
            source_node="retrieval",
            error_type="TimeoutError",
            message="simulated Pinecone timeout",
        ),
    }
    merged = {**state_in, **retrieval_out}
    assert merged.get("degraded_mode") is True
    assert merged.get("failure_chain")
    skip, _ = should_skip_tools(merged)
    assert skip is True
    print("retrieval failure cascade + tool skip: OK")


async def main() -> None:
    test_initial_collaboration_state()
    test_butterfly_effect_assessment()
    test_retrieval_escalation_routing()
    test_tools_circuit_breaker()
    test_sanitize_tool_errors()
    test_validation_correction_routing()
    test_graph_compiles_with_collaboration_edges()
    await test_retrieval_failure_cascade()
    await test_agent_run_records_handoffs()
    print("\nAll multi-agent collaboration tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
