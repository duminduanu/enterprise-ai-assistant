"""Server-Sent Events formatting for agent activity and token streams."""

from __future__ import annotations

import json
from typing import Any


def format_sse(*, event: str, data: dict[str, Any]) -> dict[str, str]:
    """Return an sse-starlette compatible event dict."""
    return {
        "event": event,
        "data": json.dumps(data, default=str),
    }


def sse_started(*, session_id: str, request_id: str) -> dict[str, str]:
    return format_sse(
        event="started",
        data={"session_id": session_id, "request_id": request_id},
    )


def sse_node(*, node: str, status: str, **metadata: Any) -> dict[str, str]:
    return format_sse(
        event="node",
        data={"node": node, "status": status, **metadata},
    )


def sse_agent_event(event: dict[str, Any]) -> dict[str, str]:
    return format_sse(event="agent_event", data=event)


def sse_token(content: str) -> dict[str, str]:
    return format_sse(event="token", data={"content": content})


def sse_done(payload: dict[str, Any]) -> dict[str, str]:
    return format_sse(event="done", data=payload)


def sse_error(message: str, *, request_id: str | None = None) -> dict[str, str]:
    return format_sse(
        event="error",
        data={"error": message, "request_id": request_id},
    )
