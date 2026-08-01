#!/usr/bin/env python3
"""Send traced retrieval (+ optional chat) calls to LangSmith for verification."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.observability.langsmith_config import configure_langsmith, is_tracing_enabled  # noqa: E402
from backend.app.retrieval import HybridRetriever  # noqa: E402


async def run_search(query: str, role: str) -> None:
    retriever = HybridRetriever()
    hits = await retriever.asearch(query, user_role=role)
    print(f"Retrieval returned {len(hits)} hits")
    for hit in hits[:3]:
        print(f"  - {hit.source_file} (score={hit.hybrid_score:.4f})")


async def run_chat(query: str) -> None:
    from httpx import ASGITransport, AsyncClient

    from backend.app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            json={"message": query, "user_role": "analyst"},
        )
        print(f"Chat status: {response.status_code}")
        if response.is_success:
            data = response.json()
            print(f"Answer preview: {data.get('answer', '')[:160]}...")
            print(f"Citations: {data.get('retrieval_count', 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify LangSmith tracing")
    parser.add_argument("query", nargs="?", default="payment failure outage")
    parser.add_argument("--role", default="analyst", choices=["viewer", "analyst", "admin"])
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Also exercise POST /api/v1/chat (includes LLM trace if quota allows)",
    )
    args = parser.parse_args()

    settings = get_settings()
    enabled = configure_langsmith(settings)

    print(f"LangSmith project: {settings.langsmith_project}")
    print(f"Tracing enabled: {enabled} (runtime flag={is_tracing_enabled()})")

    if not enabled:
        print("\nSet LANGSMITH_API_KEY in .env and LANGSMITH_TRACING=true, then re-run.")
        sys.exit(1)

    asyncio.run(run_search(args.query, args.role))

    if args.chat:
        asyncio.run(run_chat(args.query))

    print(
        "\nOpen LangSmith -> Tracing -> "
        f"{settings.langsmith_project} to confirm new runs appear "
        "(hybrid_retrieval, search_pipeline, and chat_pipeline when using --chat)."
    )


if __name__ == "__main__":
    main()
