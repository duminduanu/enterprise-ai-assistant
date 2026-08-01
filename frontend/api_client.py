"""HTTP client for the enterprise AI assistant FastAPI backend."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class SSEMessage:
    event: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamResult:
    answer: str = ""
    session_id: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    agent_events: list[dict[str, Any]] = field(default_factory=list)
    route: str | None = None
    validation_passed: bool | None = None
    model: str | None = None
    error: str | None = None


class AssistantApiClient:
    def __init__(self, base_url: str, *, timeout: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(
        self,
        token: str | None = None,
        role: str | None = None,
    ) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif role:
            headers["X-User-Role"] = role
        return headers

    def health_ok(self) -> bool:
        try:
            with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
                response = client.get("/health")
                response.raise_for_status()
                return response.json().get("status") in {"ok", "degraded"}
        except Exception:
            return False

    def login(self, email: str, password: str) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            response.raise_for_status()
            return response.json()

    def stream_chat(
        self,
        message: str,
        *,
        session_id: str | None,
        token: str | None = None,
        role: str | None = None,
    ) -> Iterator[SSEMessage]:
        payload: dict[str, Any] = {"message": message}
        if session_id:
            payload["session_id"] = session_id

        headers = self._headers(token, role)
        headers["Accept"] = "text/event-stream"

        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            with client.stream(
                "POST",
                "/api/v1/chat/stream",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()
                yield from _parse_sse_lines(response.iter_lines())

    def consume_stream(
        self,
        message: str,
        *,
        session_id: str | None,
        token: str | None = None,
        role: str | None = None,
        on_event: Callable[[SSEMessage], None] | None = None,
    ) -> StreamResult:
        """Collect SSE events; optionally invoke ``on_event(SSEMessage)`` for live UI updates."""
        result = StreamResult()
        answer_parts: list[str] = []

        for msg in self.stream_chat(
            message,
            session_id=session_id,
            token=token,
            role=role,
        ):
            if on_event is not None:
                on_event(msg)

            if msg.event == "started":
                result.session_id = msg.data.get("session_id", result.session_id)
            elif msg.event == "token":
                answer_parts.append(msg.data.get("content", ""))
            elif msg.event == "agent_event":
                result.agent_events.append(msg.data)
            elif msg.event == "node":
                result.route = msg.data.get("route") or result.route
            elif msg.event == "done":
                result.answer = msg.data.get("answer", "".join(answer_parts))
                result.session_id = msg.data.get("session_id", result.session_id)
                result.citations = msg.data.get("citations") or []
                result.agent_events = msg.data.get("agent_events") or result.agent_events
                result.route = msg.data.get("route")
                result.validation_passed = msg.data.get("validation_passed")
                result.model = msg.data.get("model")
            elif msg.event == "error":
                result.error = msg.data.get("error", "Unknown error")

        if not result.answer and answer_parts:
            result.answer = "".join(answer_parts)
        return result


def _parse_sse_lines(lines: Iterator[str]) -> Iterator[SSEMessage]:
    current_event = "message"
    data_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if data_lines:
                yield SSEMessage(
                    event=current_event,
                    data=json.loads("\n".join(data_lines)),
                )
            current_event = "message"
            data_lines = []
            continue
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())

    if data_lines:
        yield SSEMessage(event=current_event, data=json.loads("\n".join(data_lines)))
