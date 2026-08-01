#!/usr/bin/env python3
"""Test RLM batch decomposition on a complex research query."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.agents.rlm import run_rlm_pipeline  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402
from backend.app.observability.langsmith_config import configure_langsmith  # noqa: E402
from backend.app.retrieval import HybridRetriever  # noqa: E402


async def main_async(query: str, role: str) -> None:
    settings = get_settings()
    configure_langsmith(settings)

    state = {
        "user_question": query,
        "user_role": role,
        "session_id": "rlm-test",
        "request_id": "rlm-test-request",
        "department": None,
        "document_type": None,
    }

    result = await run_rlm_pipeline(
        question=query,
        state=state,
        retriever=HybridRetriever(),
    )

    print(f"Objective: {result.plan.objective}")
    print(f"Batches: {len(result.plan.batches)}")
    for batch in result.plan.batches:
        print(f"  - {batch.batch_id}: {batch.focus} -> {batch.query}")

    print(f"\nMerged chunks: {len(result.retrieved_docs)}")
    print("\nBatch summaries:")
    for br in result.batch_results:
        print(f"\n[{br.batch.batch_id}] {br.batch.focus}")
        print(br.summary[:400])

    print("\nResearch notes:")
    print(result.research_notes[:600])

    print("\nRLM agent events:")
    for event in result.agent_events:
        print(f"  - {event.get('event_type')}: {event.get('message')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test RLM batch decomposition")
    parser.add_argument(
        "query",
        nargs="?",
        default="Summarize payment outage reports from last year",
    )
    parser.add_argument("--role", default="analyst", choices=["viewer", "analyst", "admin"])
    args = parser.parse_args()
    asyncio.run(main_async(args.query, args.role))


if __name__ == "__main__":
    main()
