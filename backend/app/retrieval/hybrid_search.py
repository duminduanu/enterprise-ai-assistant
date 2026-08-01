"""Hybrid retrieval: dense (Pinecone) + sparse (BM25) with RBAC filtering."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.app.retrieval.config import (
    ROLE_ACCESS_LEVELS,
    RetrievalSettings,
    load_retrieval_settings,
)
from backend.app.retrieval.dense_search import DenseSearch
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit
from backend.app.retrieval.sparse_search import SparseSearch

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combine dense and sparse retrieval with configurable alpha weighting."""

    def __init__(self, settings: RetrievalSettings | None = None) -> None:
        self.settings = settings or load_retrieval_settings()
        self._dense = DenseSearch(self.settings)
        self._sparse = SparseSearch(self.settings)

    def search(
        self,
        query: str,
        *,
        user_role: str = "viewer",
        top_k: int | None = None,
        filters: RetrievalFilters | None = None,
        alpha: float | None = None,
    ) -> list[RetrievalHit]:
        """
        Run hybrid search and return ranked hits with source attribution.

        final_score = alpha * dense_score_norm + (1 - alpha) * sparse_score_norm
        """
        top_k = top_k or self.settings.top_k
        candidate_k = self.settings.candidate_k
        alpha = alpha if alpha is not None else self.settings.hybrid_alpha

        dense_hits = self._dense.search(query, top_k=candidate_k, filters=filters)
        sparse_hits = self._sparse.search(query, top_k=candidate_k, filters=filters)

        merged = _merge_hits(dense_hits, sparse_hits, alpha=alpha)
        filtered = _apply_rbac(merged, user_role=user_role)
        filtered.sort(key=lambda h: h.hybrid_score, reverse=True)

        logger.info(
            "Hybrid search query=%r role=%s dense=%d sparse=%d merged=%d returned=%d",
            query[:80],
            user_role,
            len(dense_hits),
            len(sparse_hits),
            len(merged),
            min(top_k, len(filtered)),
        )
        return filtered[:top_k]

    async def asearch(
        self,
        query: str,
        *,
        user_role: str = "viewer",
        top_k: int | None = None,
        filters: RetrievalFilters | None = None,
        alpha: float | None = None,
    ) -> list[RetrievalHit]:
        """Async wrapper for use in FastAPI / LangGraph nodes."""
        return await asyncio.to_thread(
            self.search,
            query,
            user_role=user_role,
            top_k=top_k,
            filters=filters,
            alpha=alpha,
        )


def _merge_hits(
    dense_hits: list[RetrievalHit],
    sparse_hits: list[RetrievalHit],
    *,
    alpha: float,
) -> list[RetrievalHit]:
    dense_norm = _normalize_scores({h.chunk_id: h.dense_score for h in dense_hits})
    sparse_norm = _normalize_scores({h.chunk_id: h.sparse_score for h in sparse_hits})

    combined: dict[str, RetrievalHit] = {}

    for hit in dense_hits:
        combined[hit.chunk_id] = RetrievalHit(
            chunk_id=hit.chunk_id,
            text=hit.text,
            source_file=hit.source_file,
            namespace=hit.namespace,
            metadata=hit.metadata,
            dense_score=hit.dense_score,
            sparse_score=0.0,
            section_heading=hit.section_heading,
            title=hit.title,
        )

    for hit in sparse_hits:
        if hit.chunk_id in combined:
            existing = combined[hit.chunk_id]
            existing.sparse_score = hit.sparse_score
            if not existing.text:
                existing.text = hit.text
        else:
            combined[hit.chunk_id] = RetrievalHit(
                chunk_id=hit.chunk_id,
                text=hit.text,
                source_file=hit.source_file,
                namespace=hit.namespace,
                metadata=hit.metadata,
                sparse_score=hit.sparse_score,
                section_heading=hit.section_heading,
                title=hit.title,
            )

    for chunk_id, hit in combined.items():
        d = dense_norm.get(chunk_id, 0.0)
        s = sparse_norm.get(chunk_id, 0.0)
        hit.hybrid_score = alpha * d + (1.0 - alpha) * s

    return list(combined.values())


def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return {k: 0.0 for k in scores}
    return {k: v / max_score for k, v in scores.items()}


def _apply_rbac(hits: list[RetrievalHit], *, user_role: str) -> list[RetrievalHit]:
    allowed = ROLE_ACCESS_LEVELS.get(user_role, ROLE_ACCESS_LEVELS["viewer"])
    return [
        hit
        for hit in hits
        if str(hit.metadata.get("access_level", "internal")) in allowed
    ]


def hits_to_citations(hits: list[RetrievalHit]) -> list[dict[str, Any]]:
    """Format hits as citation objects for agent responses."""
    return [hit.to_dict() for hit in hits]
