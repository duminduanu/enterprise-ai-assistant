"""MCP client for Commercial Bank enterprise data server."""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp.client import Client
from mcp_types import CallToolResult, TextContent

from backend.app.core.config import get_settings
from backend.app.core.fallbacks import mcp_failure_payload

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.server import create_server  # noqa: E402

_client: Client | None = None
_exit_stack: AsyncExitStack | None = None
_client_lock = asyncio.Lock()


def _extract_tool_text(result: CallToolResult) -> str:
    if result.is_error:
        return f"MCP tool error: {result.content}"
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(str(block.text))
        else:
            parts.append(str(block))
    return "\n".join(parts) if parts else ""


async def get_mcp_client() -> Client:
    """Lazy singleton in-process MCP client."""
    global _client, _exit_stack

    async with _client_lock:
        if _client is None:
            stack = AsyncExitStack()
            client = await stack.enter_async_context(Client(create_server()))
            _exit_stack = stack
            _client = client
        return _client


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    settings = get_settings()
    try:
        client = await get_mcp_client()
        result = await asyncio.wait_for(
            client.call_tool(name, arguments),
            timeout=settings.mcp_timeout_seconds,
        )
        return _extract_tool_text(result)
    except asyncio.TimeoutError:
        logger.warning("MCP tool %s timed out after %ss", name, settings.mcp_timeout_seconds)
        return mcp_failure_payload(name, "lookup timed out")
    except Exception as exc:
        logger.warning("MCP tool %s failed: %s", name, exc)
        return mcp_failure_payload(name, str(exc)[:200])


async def close_mcp_client() -> None:
    global _client, _exit_stack
    async with _client_lock:
        if _exit_stack is not None:
            await _exit_stack.aclose()
        _client = None
        _exit_stack = None
