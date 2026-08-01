#!/usr/bin/env python3
"""Test LangGraph multi-agent workflow from the command line."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.agents.runner import run_agent  # noqa: E402
from backend.app.observability.langsmith_config import configure_langsmith  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402


async def main_async(query: str, role: str) -> None:
    settings = get_settings()
    configure_langsmith(settings)

    result = await run_agent(
        message=query,
        user_role=role,
        session_id="test-session",
        request_id="test-request",
    )

    print(f"Route: {result.get('route')}")
    print(f"Plan: {result.get('plan')}")
    print(f"Current node: {result.get('current_node')}")
    print(f"Validation passed: {result.get('validation_passed')}")
    print(f"Retrieved chunks: {len(result.get('retrieved_docs') or [])}")
    print("\nAgent events:")
    for event in result.get("agent_events") or []:
        print(f"  - [{event.get('node')}] {event.get('event_type')}: {event.get('message')}")

    print("\nAnswer preview:")
    print((result.get("final_answer") or "")[:500])


def main() -> None:
    parser = argparse.ArgumentParser(description="Test LangGraph agent")
    parser.add_argument("query", nargs="?", default="What is the password reset policy?")
    parser.add_argument("--role", default="analyst", choices=["viewer", "analyst", "admin"])
    args = parser.parse_args()
    asyncio.run(main_async(args.query, args.role))


if __name__ == "__main__":
    main()
