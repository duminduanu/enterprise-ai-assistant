"""JWT creation and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from backend.app.core.config import get_settings

ALGORITHM = "HS256"
TOKEN_TYPE = "bearer"


def create_access_token(
    *,
    user_id: str,
    email: str,
    role: str,
    display_name: str,
    expires_minutes: int | None = None,
) -> str:
    settings = get_settings()
    expire_minutes = expires_minutes or settings.jwt_expire_minutes
    expire = datetime.now(UTC) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


def safe_decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_access_token(token)
    except JWTError:
        return None
