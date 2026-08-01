"""LLM and embedding provider factory (Google Gemini)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langsmith import traceable

ProviderName = Literal["gemini"]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"


@dataclass(frozen=True)
class ProviderSettings:
    llm_provider: ProviderName
    llm_model: str
    embedding_provider: ProviderName
    embedding_model: str
    embedding_dimension: int
    google_api_key: str


def load_provider_settings(env_path: str | None = None) -> ProviderSettings:
    """Load provider configuration from environment variables."""
    load_dotenv(env_path or PROJECT_ROOT / ".env", override=True)

    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY is required for Gemini provider")

    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "gemini").lower()

    if llm_provider != "gemini" or embedding_provider != "gemini":
        raise ValueError(
            "Only Gemini provider is configured in this POC. "
            "Set LLM_PROVIDER=gemini and EMBEDDING_PROVIDER=gemini."
        )

    return ProviderSettings(
        llm_provider="gemini",
        llm_model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
        embedding_provider="gemini",
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
        google_api_key=google_api_key,
    )


@lru_cache(maxsize=1)
def get_chat_llm(
    model: str | None = None,
    temperature: float = 0.2,
) -> ChatGoogleGenerativeAI:
    """Return a LangChain chat model for agent orchestration."""
    settings = load_provider_settings()
    return ChatGoogleGenerativeAI(
        model=model or settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


def get_embeddings(model: str | None = None) -> GoogleGenerativeAIEmbeddings:
    """Return a LangChain embeddings model for dense retrieval."""
    settings = load_provider_settings()
    embedding_model = model or settings.embedding_model
    # Strip legacy "models/" prefix; retired models like text-embedding-004 must not be used.
    if embedding_model.startswith("models/"):
        embedding_model = embedding_model.removeprefix("models/")

    kwargs: dict = {
        "model": embedding_model,
        "google_api_key": settings.google_api_key,
    }
    # gemini-embedding-001 supports reduced dimensionality for Pinecone 768-dim indexes.
    if embedding_model == "gemini-embedding-001":
        kwargs["output_dimensionality"] = settings.embedding_dimension
        kwargs["task_type"] = "RETRIEVAL_DOCUMENT"

    return GoogleGenerativeAIEmbeddings(**kwargs)


def embed_texts(
    texts: list[str],
    *,
    task_type: str = "retrieval_document",
    max_retries: int = 5,
) -> list[list[float]]:
    """
    Embed a batch of texts using Gemini.

    task_type: 'retrieval_document' for ingestion, 'retrieval_query' for search queries.
    """
    settings = load_provider_settings()
    embeddings_client = get_embeddings()

    for attempt in range(max_retries):
        try:
            vectors = embeddings_client.embed_documents(texts)
            if vectors and len(vectors[0]) != settings.embedding_dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: got {len(vectors[0])}, "
                    f"expected {settings.embedding_dimension}. "
                    "Update EMBEDDING_DIMENSION or recreate the Pinecone index."
                )
            return vectors
        except Exception as exc:
            err = str(exc).lower()
            if "quota" in err or "rate" in err or "429" in err or "resource_exhausted" in err:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        "Gemini API quota or rate limit exceeded. "
                        "Free tier allows ~100 embed requests/minute. "
                        "Wait 60 seconds and re-run ingestion (upserts are idempotent), "
                        "or set INGEST_BATCH_SIZE=5 and INGEST_DELAY_SECONDS=1.5 in .env."
                    ) from exc
                wait = max(30, 2 ** attempt)
                time.sleep(wait)
                continue
            raise

    raise RuntimeError("Failed to embed texts after retries")


@traceable(name="embed_query", run_type="embedding")
def embed_query(query: str) -> list[float]:
    """Embed a single search query."""
    settings = load_provider_settings()
    embedding_model = settings.embedding_model.removeprefix("models/")
    kwargs: dict = {
        "model": embedding_model,
        "google_api_key": settings.google_api_key,
    }
    if embedding_model == "gemini-embedding-001":
        kwargs["output_dimensionality"] = settings.embedding_dimension
        kwargs["task_type"] = "RETRIEVAL_QUERY"
    client = GoogleGenerativeAIEmbeddings(**kwargs)
    return client.embed_query(query)
