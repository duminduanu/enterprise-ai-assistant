"""Shared data access for MCP enterprise tools."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def load_employees() -> list[dict[str, Any]]:
    return _load_json("employees.json")


@lru_cache(maxsize=1)
def load_services() -> list[dict[str, Any]]:
    return _load_json("services.json")


@lru_cache(maxsize=1)
def load_incidents() -> list[dict[str, Any]]:
    return _load_json("incidents.json")


def _load_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _match(query: str, record: dict[str, Any], fields: list[str]) -> bool:
    q = query.lower().strip()
    if not q:
        return False
    haystack = " ".join(str(record.get(field, "")) for field in fields).lower()
    return q in haystack or any(token in haystack for token in q.split() if len(token) > 2)


def search_employees(query: str, limit: int = 5) -> list[dict[str, Any]]:
    fields = ["name", "email", "department", "title", "employee_id"]
    matches = [r for r in load_employees() if _match(query, r, fields)]
    return matches[:limit]


def search_services(query: str, limit: int = 5) -> list[dict[str, Any]]:
    fields = ["name", "service_id", "description", "owner", "owner_email", "dependencies"]
    matches = [r for r in load_services() if _match(query, r, fields)]
    return matches[:limit]


def search_incidents(query: str, limit: int = 5) -> list[dict[str, Any]]:
    fields = ["incident_id", "title", "service", "owner", "status", "severity"]
    matches = [r for r in load_incidents() if _match(query, r, fields)]
    return matches[:limit]
