#!/usr/bin/env python3
"""Test graceful error handling and async execution paths."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.exceptions import AgentTimeoutError  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.retrieval.hybrid_search import HybridRetriever  # noqa: E402


async def test_invalid_request_422() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Role": "viewer"},
            json={"message": "   "},
        )
        assert response.status_code == 400, response.text
        print("whitespace-only message -> 400: OK")


async def test_health_async() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        response.raise_for_status()
        data = response.json()
        assert data["status"] in {"ok", "degraded"}
        assert "bm25_corpus" in data["services"]
        print(f"health async check ({data['status']}): OK")


async def test_dense_fallback_to_sparse() -> None:
    retriever = HybridRetriever()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated Pinecone outage")

    with patch.object(retriever._dense, "search", side_effect=boom):
        hits = await retriever.asearch("payment failure outage", user_role="viewer", top_k=3)

    assert hits, "sparse-only fallback should still return results"
    print(f"dense failure -> sparse fallback ({len(hits)} hits): OK")


async def test_agent_timeout_graceful() -> None:
    from backend.app.agents import runner as runner_module
    from backend.app.core.config import Settings

    base = get_settings()
    fast_settings = Settings(
        **{
            **base.model_dump(),
            "agent_timeout_seconds": 1,
        }
    )

    async def slow_graph(*args, **kwargs):
        await asyncio.sleep(3)
        return {"final_answer": "should not reach"}

    with (
        patch.object(runner_module, "get_compiled_agent_graph") as mock_graph,
        patch.object(runner_module, "get_settings", return_value=fast_settings),
    ):
        mock_graph.return_value.ainvoke = slow_graph
        result = await runner_module.run_agent(
            message="What is the password policy?",
            user_role="viewer",
            session_id="timeout-test",
            request_id="req-timeout",
        )

    assert "timed out" in result["final_answer"].lower() or "too long" in result["final_answer"].lower()
    timeout_events = [
        e for e in result.get("agent_events", []) if e.get("event_type") == "agent_timeout"
    ]
    assert timeout_events, "expected agent_timeout event"
    print("agent timeout graceful fallback: OK")


def test_exception_types() -> None:
    err = AgentTimeoutError("slow agent")
    assert err.status_code == 504
    print("AgentTimeoutError status 504: OK")


async def main_async() -> None:
    test_exception_types()
    await test_invalid_request_422()
    await test_health_async()
    await test_dense_fallback_to_sparse()
    await test_agent_timeout_graceful()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
