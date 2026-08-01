"""knowledge_search tool — hybrid RAG over the enterprise knowledge base."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.app.retrieval import HybridRetriever
from backend.app.retrieval.schemas import RetrievalFilters


class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum results to return")
    department: str | None = Field(default=None, description="Optional department filter")
    document_type: str | None = Field(default=None, description="Optional document type filter")
    user_role: str = Field(default="viewer", description="RBAC role: viewer, analyst, or admin")


def create_knowledge_search_tool(retriever: HybridRetriever) -> StructuredTool:
    """Build a LangChain tool wrapping HybridRetriever."""

    async def knowledge_search(
        query: str,
        top_k: int = 5,
        department: str | None = None,
        document_type: str | None = None,
        user_role: str = "viewer",
    ) -> str:
        """
        Search Commercial Bank internal documents using hybrid dense+sparse retrieval.

        Returns JSON list of chunks with source attribution and hybrid scores.
        """
        filters = RetrievalFilters(department=department, document_type=document_type)
        hits = await retriever.asearch(
            query,
            user_role=user_role,
            top_k=top_k,
            filters=filters,
        )
        results: list[dict[str, Any]] = []
        for hit in hits:
            doc = hit.to_dict()
            doc["text"] = hit.text
            results.append(doc)
        return json.dumps(results, indent=2)

    return StructuredTool.from_function(
        coroutine=knowledge_search,
        name="knowledge_search",
        description=(
            "Search the internal knowledge base (incidents, runbooks, policies, "
            "architecture docs, meeting notes). Use for factual lookup and evidence gathering."
        ),
        args_schema=KnowledgeSearchInput,
    )
