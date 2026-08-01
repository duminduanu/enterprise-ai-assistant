"""Shared schemas for retrieval results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalFilters:
    """Optional metadata filters applied during hybrid search."""

    department: str | None = None
    document_type: str | None = None
    namespace: str | None = None
    min_created_date: str | None = None
    max_created_date: str | None = None


@dataclass
class RetrievalHit:
    """A single retrieved chunk with hybrid scores and source attribution."""

    chunk_id: str
    text: str
    source_file: str
    namespace: str
    metadata: dict[str, Any]
    dense_score: float = 0.0
    sparse_score: float = 0.0
    hybrid_score: float = 0.0
    section_heading: str = ""
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "title": self.title,
            "source_file": self.source_file,
            "namespace": self.namespace,
            "section_heading": self.section_heading,
            "dense_score": round(self.dense_score, 4),
            "sparse_score": round(self.sparse_score, 4),
            "hybrid_score": round(self.hybrid_score, 4),
            "access_level": self.metadata.get("access_level"),
            "department": self.metadata.get("department"),
            "document_type": self.metadata.get("document_type"),
            "text_preview": self.text[:300],
        }
