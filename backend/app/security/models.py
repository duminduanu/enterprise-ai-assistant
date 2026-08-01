"""Authenticated user model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

UserRole = Literal["viewer", "analyst", "admin"]


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str
    role: UserRole
    display_name: str
