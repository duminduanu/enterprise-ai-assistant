"""Execute the LangGraph agent workflow from API handlers."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langsmith import traceable

from backend.app.agents.graph import get_compiled_agent_graph
from backend.app.observability.langsmith_config import build_run_config
from backend.app.retrieval.schemas import RetrievalHit

logger = logging.getLogger(__name__)


@traceable(name="langgraph_agent_run", run_type="chain")
async def run_agent(
    *,
    message: str,
    user_role: str,
    session_id: str,
    request_id: str,
    department: str | None = None,
    document_type: str | None = None,
) -> dict[str, Any]:
    graph = get_compiled_agent_graph()
    initial_state = {
        "messages": [HumanMessage(content=message)],
        "user_question": message,
        "user_role": user_role,
        "session_id": session_id,
        "request_id": request_id,
        "department": department,
        "document_type": document_type,
        "retrieved_docs": [],
        "tool_calls": [],
        "agent_events": [],
        "validation_issues": [],
    }

    config = build_run_config(
        run_name="enterprise_agent",
        request_id=request_id,
        session_id=session_id,
        user_role=user_role,
        tags=["langgraph", "multi-agent"],
        metadata={"question_preview": message[:120]},
    )

    result = await graph.ainvoke(initial_state, config=config)
    return result


def docs_to_hits(docs: list[dict[str, Any]]) -> list[RetrievalHit]:
    """Convert serialized retrieval docs back to RetrievalHit for API citations."""
    hits: list[RetrievalHit] = []
    for doc in docs:
        hits.append(
            RetrievalHit(
                chunk_id=doc.get("chunk_id", ""),
                text=doc.get("text") or doc.get("text_preview", ""),
                source_file=doc.get("source_file", ""),
                namespace=doc.get("namespace", ""),
                metadata={
                    "access_level": doc.get("access_level"),
                    "department": doc.get("department"),
                    "document_type": doc.get("document_type"),
                },
                dense_score=float(doc.get("dense_score") or 0.0),
                sparse_score=float(doc.get("sparse_score") or 0.0),
                hybrid_score=float(doc.get("hybrid_score") or 0.0),
                section_heading=doc.get("section_heading", ""),
                title=doc.get("title", ""),
            )
        )
    return hits
