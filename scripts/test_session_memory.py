#!/usr/bin/env python3
"""Test multi-turn session memory across agent runs."""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.agents.runner import run_agent  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402
from backend.app.memory.session_store import get_session_store  # noqa: E402
from backend.app.observability.langsmith_config import configure_langsmith  # noqa: E402


async def main_async() -> None:
    settings = get_settings()
    configure_langsmith(settings)

    session_id = str(uuid.uuid4())
    store = get_session_store()

    q1 = "What is the password reset policy?"
    r1 = await run_agent(
        message=q1,
        user_role="analyst",
        session_id=session_id,
        request_id="mem-test-1",
    )
    print(f"Turn 1 history_turns before run: {r1.get('history_turns')}")
    print(f"Stored turns after turn 1: {len(r1.get('chat_history') or [])}")

    q2 = "What are the requirements for it?"
    r2 = await run_agent(
        message=q2,
        user_role="analyst",
        session_id=session_id,
        request_id="mem-test-2",
    )
    print(f"\nTurn 2 history_turns before run: {r2.get('history_turns')}")
    print(f"Stored turns after turn 2: {len(r2.get('chat_history') or [])}")

    history = await store.get_history(session_id)
    print("\nSession history:")
    for turn in history:
        preview = turn.get("content", "")[:80].replace("\n", " ")
        print(f"  [{turn.get('role')}] {preview}...")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
