"""Sparse BM25 keyword search over ingested corpus."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from backend.app.retrieval.config import RetrievalSettings
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


@lru_cache(maxsize=1)
def _load_corpus(corpus_path: str) -> tuple[list[dict], BM25Okapi]:
    path = corpus_path
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    tokenized = [_tokenize(record["text"]) for record in records]
    bm25 = BM25Okapi(tokenized)
    return records, bm25


class SparseSearch:
    """In-process BM25 search using corpus saved during ingestion."""

    def __init__(self, settings: RetrievalSettings) -> None:
        self._settings = settings
        if not settings.bm25_corpus_path.exists():
            raise FileNotFoundError(
                f"BM25 corpus not found at {settings.bm25_corpus_path}. "
                "Run: python scripts/ingest_documents.py --dry-run"
            )
        self._records, self._bm25 = _load_corpus(str(settings.bm25_corpus_path))

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievalHit]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )

        hits: list[RetrievalHit] = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score <= 0:
                break

            record = self._records[idx]
            metadata = dict(record.get("metadata", {}))

            if not _passes_filters(record, metadata, filters):
                continue

            hits.append(
                RetrievalHit(
                    chunk_id=record["id"],
                    text=record["text"],
                    source_file=metadata.get("source_file", ""),
                    namespace=record.get("namespace", ""),
                    metadata=metadata,
                    sparse_score=score,
                    section_heading=metadata.get("section_heading", ""),
                    title=metadata.get("title", ""),
                )
            )
            if len(hits) >= top_k:
                break

        return hits


def _passes_filters(
    record: dict,
    metadata: dict,
    filters: RetrievalFilters | None,
) -> bool:
    if not filters:
        return True

    if filters.namespace and record.get("namespace") != filters.namespace:
        return False
    if filters.department and metadata.get("department") != filters.department:
        return False
    if filters.document_type and metadata.get("document_type") != filters.document_type:
        return False

    created = metadata.get("created_date", "")
    if filters.min_created_date and created and created < filters.min_created_date:
        return False
    if filters.max_created_date and created and created > filters.max_created_date:
        return False

    return True
