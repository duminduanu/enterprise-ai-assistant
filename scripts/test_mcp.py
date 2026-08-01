#!/usr/bin/env python3
"""Test MCP server tools directly and via the agent."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.tools.mcp_client import call_mcp_tool, close_mcp_client  # noqa: E402


async def test_direct(query: str) -> None:
    print("lookup_service:")
    print(await call_mcp_tool("lookup_service", {"query": query}))


async def test_agent(query: str) -> None:
    from backend.app.agents.runner import run_agent
    from backend.app.core.config import get_settings
    from backend.app.observability.langsmith_config import configure_langsmith

    configure_langsmith(get_settings())
    result = await run_agent(
        message=query,
        user_role="analyst",
        session_id="mcp-test",
        request_id="mcp-test-request",
    )
    print(f"Route: {result.get('route')}")
    print(f"MCP results preview:\n{(result.get('mcp_results') or '')[:600]}")
    print("\nTool agent events:")
    for event in result.get("agent_events") or []:
        if event.get("node") == "tools":
            print(f"  - {event.get('event_type')}: {event.get('message')}")


async def main_async(service_query: str, run_agent_test: bool) -> None:
    try:
        await test_direct(service_query)
        if run_agent_test:
            print("\n--- Full agent run ---")
            await test_agent("Who owns the payments service?")
    finally:
        await close_mcp_client()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test MCP enterprise server")
    parser.add_argument("query", nargs="?", default="payments")
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Also run full agent with 'Who owns the payments service?'",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.query, args.agent))


if __name__ == "__main__":
    main()
