"""FastAPI dependencies."""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, Request

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import UnauthorizedError
from backend.app.retrieval import HybridRetriever
from backend.app.security.jwt import safe_decode_access_token
from backend.app.security.models import CurrentUser
from backend.app.security.rbac import normalize_role


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever()


def get_request_id(request: Request) -> str:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


SettingsDep = Annotated[Settings, Depends(get_settings)]
RetrieverDep = Annotated[HybridRetriever, Depends(get_retriever)]


def _user_from_bearer(authorization: str | None) -> CurrentUser | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    payload = safe_decode_access_token(token)
    if payload is None:
        return None
    return CurrentUser(
        user_id=str(payload.get("sub", "")),
        email=str(payload.get("email", "")),
        role=normalize_role(str(payload.get("role", "viewer"))),
        display_name=str(payload.get("name", "")),
    )


async def get_current_user(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """
    Resolve the authenticated user from JWT Bearer token.

    When AUTH_REQUIRED=false (POC/dev), falls back to X-User-Role header.
    """
    user = _user_from_bearer(authorization)
    if user is not None:
        return user

    if settings.auth_required:
        raise UnauthorizedError("Valid Bearer token required")

    role = normalize_role(x_user_role)
    return CurrentUser(
        user_id="anonymous",
        email="anonymous@local",
        role=role,
        display_name=f"Anonymous ({role})",
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
