"""Role-based access control helpers."""

from __future__ import annotations

from typing import Literal

Role = Literal["viewer", "analyst", "admin"]

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {"chat", "search"},
    "analyst": {"chat", "search", "python_analysis", "mcp_lookup", "research"},
    "admin": {"chat", "search", "python_analysis", "mcp_lookup", "research", "restricted_docs"},
}

TOOL_PERMISSIONS: dict[str, str] = {
    "knowledge_search": "chat",
    "python_analysis": "python_analysis",
    "lookup_employee": "mcp_lookup",
    "lookup_service": "mcp_lookup",
    "lookup_incident": "mcp_lookup",
}


def normalize_role(role: str | None) -> Role:
    value = (role or "viewer").lower()
    if value in {"viewer", "analyst", "admin"}:
        return value  # type: ignore[return-value]
    return "viewer"


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), set())


def can_use_tool(role: str, tool_name: str) -> bool:
    permission = TOOL_PERMISSIONS.get(tool_name, "chat")
    return has_permission(role, permission)


def can_use_research_route(role: str) -> bool:
    return has_permission(role, "research")


def can_access_restricted_docs(role: str) -> bool:
    return has_permission(role, "restricted_docs")
