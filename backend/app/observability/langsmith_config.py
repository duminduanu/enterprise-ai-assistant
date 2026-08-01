"""LangSmith tracing configuration and run metadata helpers."""

from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.runnables import RunnableConfig

from backend.app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://api.smith.langchain.com"
_tracing_enabled = False


def configure_langsmith(settings: Settings | None = None) -> bool:
    """
    Configure LangSmith / LangChain tracing from application settings.

    Sets standard env vars consumed automatically by LangChain and LangGraph.
    Returns True when tracing is active.
    """
    global _tracing_enabled

    settings = settings or get_settings()

    if not settings.langsmith_tracing:
        _disable_tracing_env()
        _tracing_enabled = False
        logger.info("LangSmith tracing disabled via LANGSMITH_TRACING=false")
        return False

    if not settings.langsmith_api_key:
        _disable_tracing_env()
        _tracing_enabled = False
        logger.warning(
            "LangSmith tracing requested but LANGSMITH_API_KEY is missing; traces will not be sent"
        )
        return False

    endpoint = settings.langsmith_endpoint or DEFAULT_ENDPOINT
    project = settings.langsmith_project

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGSMITH_ENDPOINT"] = endpoint

    # LangChain legacy env vars (still read by langchain-core tracers)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = project
    os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    _tracing_enabled = True
    logger.info("LangSmith tracing enabled project=%s", project)
    return True


def is_tracing_enabled() -> bool:
    return _tracing_enabled


def build_run_config(
    *,
    run_name: str,
    request_id: str | None = None,
    session_id: str | None = None,
    user_role: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RunnableConfig:
    """Build LangChain RunnableConfig with consistent tags and metadata."""
    run_metadata: dict[str, Any] = dict(metadata or {})
    if request_id:
        run_metadata["request_id"] = request_id
    if session_id:
        run_metadata["session_id"] = session_id
    if user_role:
        run_metadata["user_role"] = user_role

    run_tags = ["enterprise-ai-assistant"]
    if tags:
        run_tags.extend(tags)
    if user_role:
        run_tags.append(f"role:{user_role}")

    return RunnableConfig(
        run_name=run_name,
        tags=run_tags,
        metadata=run_metadata,
    )


def trace_metadata(
    *,
    request_id: str | None = None,
    session_id: str | None = None,
    user_role: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Metadata dict for @traceable runs outside LangChain invoke."""
    data: dict[str, Any] = dict(extra)
    if request_id:
        data["request_id"] = request_id
    if session_id:
        data["session_id"] = session_id
    if user_role:
        data["user_role"] = user_role
    return data


def _disable_tracing_env() -> None:
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
