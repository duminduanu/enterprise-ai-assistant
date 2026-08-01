"""Async helpers for non-blocking I/O and bounded waits."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from backend.app.core.exceptions import AgentTimeoutError, LLMError, ToolTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_blocking(func: Callable[..., T], /, *args, **kwargs) -> T:
    """Run a blocking callable in the default thread pool."""
    return await asyncio.to_thread(func, *args, **kwargs)


async def with_timeout(
    coro: Awaitable[T],
    *,
    timeout_seconds: float,
    error_factory: Callable[[], Exception],
    operation: str,
) -> T:
    """Await `coro` with a timeout and raise a domain-specific error."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        logger.warning("%s timed out after %.1fs", operation, timeout_seconds)
        raise error_factory() from exc


async def invoke_llm(llm, messages, *, config=None, timeout_seconds: float = 45):
    """Invoke a LangChain chat model without blocking the event loop."""
    if config is None:
        return await run_blocking(llm.invoke, messages)
    return await with_timeout(
        run_blocking(llm.invoke, messages, config=config),
        timeout_seconds=timeout_seconds,
        operation="LLM invoke",
        error_factory=lambda: LLMError("LLM request timed out — try again shortly"),
    )


async def run_tool_with_timeout(coro: Awaitable[T], *, timeout_seconds: float, tool_name: str) -> T:
    return await with_timeout(
        coro,
        timeout_seconds=timeout_seconds,
        operation=f"tool {tool_name}",
        error_factory=lambda: ToolTimeoutError(f"Tool '{tool_name}' timed out after {timeout_seconds:.0f}s"),
    )


async def run_agent_with_timeout(coro: Awaitable[T], *, timeout_seconds: float) -> T:
    return await with_timeout(
        coro,
        timeout_seconds=timeout_seconds,
        operation="agent orchestration",
        error_factory=lambda: AgentTimeoutError(
            f"The assistant took too long to respond (limit: {timeout_seconds:.0f}s). "
            "Please try a simpler question."
        ),
    )
