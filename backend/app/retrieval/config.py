"""Retrieval configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from backend.app.retrieval.document_loader import FOLDER_TO_NAMESPACE

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BM25_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "bm25_corpus.json"

# RBAC: which access_level values each role may retrieve
ROLE_ACCESS_LEVELS: dict[str, set[str]] = {
    "viewer": {"public", "internal"},
    "analyst": {"public", "internal"},
    "admin": {"public", "internal", "restricted"},
}

ALL_NAMESPACES = list(FOLDER_TO_NAMESPACE.values())


@dataclass(frozen=True)
class RetrievalSettings:
    pinecone_api_key: str
    pinecone_index_name: str
    hybrid_alpha: float
    top_k: int
    candidate_k: int
    bm25_corpus_path: Path


def load_retrieval_settings() -> RetrievalSettings:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    return RetrievalSettings(
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        pinecone_index_name=os.getenv(
            "PINECONE_INDEX_NAME", "enterprise-ai-assistant-gemini"
        ),
        hybrid_alpha=float(os.getenv("HYBRID_ALPHA", "0.7")),
        top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
        candidate_k=int(os.getenv("RETRIEVAL_CANDIDATE_K", "20")),
        bm25_corpus_path=BM25_CORPUS_PATH,
    )
