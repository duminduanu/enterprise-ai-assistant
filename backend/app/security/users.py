"""Hardcoded demo users for Commercial Bank POC."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import bcrypt

Role = Literal["viewer", "analyst", "admin"]


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    email: str
    role: Role
    display_name: str
    password_hash: str


# Demo passwords (POC only): viewer123 / analyst123 / admin123
DEMO_USERS: dict[str, UserRecord] = {
    "viewer@commercialbank.com": UserRecord(
        user_id="u-viewer",
        email="viewer@commercialbank.com",
        role="viewer",
        display_name="Demo Viewer",
        password_hash="$2b$12$LRLKxprwBTrDruhNfmSUluAu/uge1eej3WrJXUII//kP7TzFfTeQq",
    ),
    "analyst@commercialbank.com": UserRecord(
        user_id="u-analyst",
        email="analyst@commercialbank.com",
        role="analyst",
        display_name="Demo Analyst",
        password_hash="$2b$12$RQ/6Cn3OGQL6ae/uABnFcu3dp1HT1Yll4uM3W6H45oLdZYAsO2qCC",
    ),
    "admin@commercialbank.com": UserRecord(
        user_id="u-admin",
        email="admin@commercialbank.com",
        role="admin",
        display_name="Demo Admin",
        password_hash="$2b$12$bM4viO/jjZCP9iUcz/h7IuymNU.UbCcbCOlM.uKDiPrmre7LxUVB2",
    ),
}


def authenticate_user(email: str, password: str) -> UserRecord | None:
    user = DEMO_USERS.get(email.strip().lower())
    if user is None:
        return None
    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return None
    return user


def get_user_by_email(email: str) -> UserRecord | None:
    return DEMO_USERS.get(email.strip().lower())
