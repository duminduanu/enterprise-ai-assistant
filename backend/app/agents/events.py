"""Agent event helpers for UI and observability."""

from __future__ import annotations

from typing import Any


def make_event(
    node: str,
    event_type: str,
    message: str,
    **metadata: Any,
) -> dict[str, Any]:
    return {
        "node": node,
        "event_type": event_type,
        "message": message,
        "metadata": metadata,
    }
