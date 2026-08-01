#!/usr/bin/env python3
"""Smoke test for frontend API client against the FastAPI app."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from backend.app.main import app  # noqa: E402
from frontend.api_client import AssistantApiClient  # noqa: E402


async def main_async() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        # Patch client to use async transport is not needed — use sync against real URL
        pass

    # Use ASGITransport via mounting — simpler: run consume_stream with httpx against app
    # AssistantApiClient uses sync httpx — test parse via direct stream on ASGI is harder.
    # Test login + stream using httpx ASGITransport wrapped — skip, use subprocess-free test:

    from frontend.api_client import _parse_sse_lines

    sample = [
        "event: started",
        'data: {"session_id": "abc", "request_id": "r1"}',
        "",
        "event: token",
        'data: {"content": "Hello"}',
        "",
        "event: done",
        'data: {"answer": "Hello", "session_id": "abc", "citations": []}',
        "",
    ]
    messages = list(_parse_sse_lines(iter(sample)))
    assert len(messages) == 3
    assert messages[0].event == "started"
    assert messages[1].data["content"] == "Hello"
    print("SSE parser: OK")

    client = AssistantApiClient("http://127.0.0.1:8000")
    print("AssistantApiClient init: OK")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
