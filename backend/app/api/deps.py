"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, Request

from backend.app.core.config import Settings, get_settings
from backend.app.retrieval import HybridRetriever


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever()


def get_request_id(request: Request) -> str:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


SettingsDep = Annotated[Settings, Depends(get_settings)]
RetrieverDep = Annotated[HybridRetriever, Depends(get_retriever)]


def get_user_role(x_user_role: Annotated[str | None, Header()] = None) -> str:
    role = (x_user_role or "viewer").lower()
    if role not in {"viewer", "analyst", "admin"}:
        return "viewer"
    return role
