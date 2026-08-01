"""Dense vector search via Pinecone."""

from __future__ import annotations

import logging
from typing import Any

from pinecone import Pinecone

from backend.app.llm.provider import embed_query
from backend.app.retrieval.config import ALL_NAMESPACES, RetrievalSettings
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit

logger = logging.getLogger(__name__)


class DenseSearch:
    """Query Pinecone index across namespaces using Gemini query embeddings."""

    def __init__(self, settings: RetrievalSettings) -> None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required for dense search")
        self._settings = settings
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index = self._pc.Index(settings.pinecone_index_name)

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        filters: RetrievalFilters | None = None,
        namespaces: list[str] | None = None,
    ) -> list[RetrievalHit]:
        query_vector = embed_query(query)
        pinecone_filter = _build_pinecone_filter(filters)
        target_namespaces = _resolve_namespaces(filters, namespaces)

        hits: list[RetrievalHit] = []
        for namespace in target_namespaces:
            try:
                response = self._index.query(
                    vector=query_vector,
                    top_k=top_k,
                    namespace=namespace,
                    include_metadata=True,
                    filter=pinecone_filter or None,
                )
            except Exception as exc:
                logger.warning("Dense search failed for namespace %s: %s", namespace, exc)
                continue

            for match in response.matches or []:
                metadata = dict(match.metadata or {})
                hits.append(
                    RetrievalHit(
                        chunk_id=match.id,
                        text=metadata.get("text", ""),
                        source_file=metadata.get("source_file", ""),
                        namespace=namespace,
                        metadata=metadata,
                        dense_score=float(match.score or 0.0),
                        section_heading=metadata.get("section_heading", ""),
                        title=metadata.get("title", ""),
                    )
                )

        hits.sort(key=lambda h: h.dense_score, reverse=True)
        return hits[:top_k]


def _resolve_namespaces(
    filters: RetrievalFilters | None,
    namespaces: list[str] | None,
) -> list[str]:
    if namespaces:
        return namespaces
    if filters and filters.namespace:
        return [filters.namespace]
    return ALL_NAMESPACES


def _build_pinecone_filter(filters: RetrievalFilters | None) -> dict[str, Any] | None:
    if not filters:
        return None

    clauses: list[dict[str, Any]] = []
    if filters.department:
        clauses.append({"department": {"$eq": filters.department}})
    if filters.document_type:
        clauses.append({"document_type": {"$eq": filters.document_type}})
    if filters.min_created_date:
        clauses.append({"created_date": {"$gte": filters.min_created_date}})
    if filters.max_created_date:
        clauses.append({"created_date": {"$lte": filters.max_created_date}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
