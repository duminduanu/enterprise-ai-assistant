#!/usr/bin/env python3
"""Ingest markdown documents into Pinecone with embeddings and metadata."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.retrieval.document_loader import load_documents  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DOCS_ROOT = ROOT / "data" / "mock_documents"
PROCESSED_DIR = ROOT / "data" / "processed"
BM25_CORPUS_PATH = PROCESSED_DIR / "bm25_corpus.json"
CHUNKS_MANIFEST_PATH = PROCESSED_DIR / "chunks_manifest.json"


def load_settings() -> dict:
    load_dotenv(ROOT / ".env")
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "pinecone_api_key": os.getenv("PINECONE_API_KEY", ""),
        "pinecone_index_name": os.getenv("PINECONE_INDEX_NAME", "enterprise-ai-assistant"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "1536")),
        "batch_size": int(os.getenv("INGEST_BATCH_SIZE", "20")),
    }


def validate_settings(settings: dict) -> None:
    missing = []
    if not settings["openai_api_key"]:
        missing.append("OPENAI_API_KEY")
    if not settings["pinecone_api_key"]:
        missing.append("PINECONE_API_KEY")
    if not settings["pinecone_index_name"]:
        missing.append("PINECONE_INDEX_NAME")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


def embed_texts(
    client: OpenAI,
    model: str,
    texts: list[str],
    max_retries: int = 5,
) -> list[list[float]]:
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except Exception as exc:
            err = str(exc)
            if "insufficient_quota" in err:
                raise RuntimeError(
                    "OpenAI API quota exceeded. Add billing/credits at "
                    "https://platform.openai.com/account/billing then re-run ingestion."
                ) from exc
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            logger.warning("Embedding retry %d/%d after error: %s", attempt + 1, max_retries, exc)
            time.sleep(wait)
    raise RuntimeError("Failed to embed texts after retries")


def upsert_batch(
    index,
    namespace: str,
    chunk_ids: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    vectors = []
    for chunk_id, embedding, metadata in zip(chunk_ids, embeddings, metadatas):
        vectors.append({"id": chunk_id, "values": embedding, "metadata": metadata})

    index.upsert(vectors=vectors, namespace=namespace)


def save_bm25_corpus(chunks) -> None:
    """Persist chunk text for in-process BM25 hybrid search (Step E)."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    corpus = [
        {
            "id": chunk.chunk_id,
            "text": chunk.text,
            "namespace": chunk.namespace,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]
    BM25_CORPUS_PATH.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    logger.info("Saved BM25 corpus (%d chunks) to %s", len(corpus), BM25_CORPUS_PATH)


def save_manifest(chunks, index_stats: dict) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    by_namespace: dict[str, int] = {}
    for chunk in chunks:
        by_namespace[chunk.namespace] = by_namespace.get(chunk.namespace, 0) + 1

    manifest = {
        "total_chunks": len(chunks),
        "chunks_by_namespace": by_namespace,
        "pinecone_index_stats": index_stats,
        "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    CHUNKS_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Saved ingestion manifest to %s", CHUNKS_MANIFEST_PATH)


def ingest(dry_run: bool = False) -> None:
    settings = load_settings()
    validate_settings(settings)

    if not DOCS_ROOT.exists():
        raise FileNotFoundError(f"Documents directory not found: {DOCS_ROOT}")

    logger.info("Loading documents from %s", DOCS_ROOT)
    chunks = load_documents(DOCS_ROOT)
    logger.info("Loaded %d chunks from markdown files", len(chunks))

    if not chunks:
        raise RuntimeError("No chunks produced — check data/mock_documents/")

    save_bm25_corpus(chunks)

    if dry_run:
        by_ns: dict[str, int] = {}
        for c in chunks:
            by_ns[c.namespace] = by_ns.get(c.namespace, 0) + 1
        logger.info("Dry run — would upsert %d chunks: %s", len(chunks), by_ns)
        return

    openai_client = OpenAI(api_key=settings["openai_api_key"])
    pc = Pinecone(api_key=settings["pinecone_api_key"])
    index = pc.Index(settings["pinecone_index_name"])

    # Group by namespace for upsert
    by_namespace: dict[str, list] = {}
    for chunk in chunks:
        by_namespace.setdefault(chunk.namespace, []).append(chunk)

    total_upserted = 0
    batch_size = settings["batch_size"]

    for namespace, ns_chunks in sorted(by_namespace.items()):
        logger.info("Upserting namespace '%s' (%d chunks)", namespace, len(ns_chunks))
        for i in range(0, len(ns_chunks), batch_size):
            batch = ns_chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            embeddings = embed_texts(
                openai_client,
                settings["embedding_model"],
                texts,
            )

            if len(embeddings[0]) != settings["embedding_dimension"]:
                raise ValueError(
                    f"Embedding dimension mismatch: got {len(embeddings[0])}, "
                    f"expected {settings['embedding_dimension']}. "
                    "Check EMBEDDING_MODEL / Pinecone index dimension."
                )

            upsert_batch(
                index,
                namespace,
                [c.chunk_id for c in batch],
                embeddings,
                [c.metadata for c in batch],
            )
            total_upserted += len(batch)
            logger.info("  Upserted batch %d–%d", i + 1, i + len(batch))
            time.sleep(0.2)  # gentle rate limit

    stats = index.describe_index_stats()
    save_manifest(chunks, stats.to_dict() if hasattr(stats, "to_dict") else dict(stats))

    logger.info("Ingestion complete — %d vectors upserted", total_upserted)
    logger.info("Pinecone index stats: %s", stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into Pinecone")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and chunk only; do not embed or upsert",
    )
    args = parser.parse_args()
    ingest(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
