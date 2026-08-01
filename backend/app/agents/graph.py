"""LangGraph multi-agent workflow definition."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from backend.app.agents.nodes import AgentNodes
from backend.app.agents.state import AgentState
from backend.app.retrieval import HybridRetriever


def route_after_supervisor(state: AgentState) -> str:
    return state.get("route") or "retrieval"


def build_agent_graph(retriever: HybridRetriever):
    """Compile supervisor -> retrieval|research -> response -> validate graph."""
    nodes = AgentNodes(retriever)

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", nodes.supervisor)
    graph.add_node("retrieval", nodes.retrieval)
    graph.add_node("research", nodes.research)
    graph.add_node("response", nodes.response)
    graph.add_node("validate", nodes.validate)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "retrieval": "retrieval",
            "research": "research",
        },
    )
    graph.add_edge("retrieval", "response")
    graph.add_edge("research", "response")
    graph.add_edge("response", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_compiled_agent_graph():
    from backend.app.api.deps import get_retriever

    return build_agent_graph(get_retriever())
