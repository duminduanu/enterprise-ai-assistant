#!/usr/bin/env python3
"""Test agent tools: knowledge_search and python_analysis."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.retrieval import HybridRetriever  # noqa: E402
from backend.app.tools.python_analysis import python_analysis  # noqa: E402
from backend.app.tools.registry import build_tools  # noqa: E402


async def test_knowledge_search(query: str, role: str) -> None:
    tools = build_tools(HybridRetriever())
    search_tool = next(t for t in tools if t.name == "knowledge_search")
    raw = await search_tool.ainvoke(
        {"query": query, "top_k": 5, "user_role": role}
    )
    docs = json.loads(raw)
    print(f"knowledge_search: {len(docs)} results for {query!r}")
    for doc in docs[:3]:
        print(f"  - {doc.get('source_file')} (score={doc.get('hybrid_score')})")


def test_python_analysis(docs_json: str, operation: str, field: str | None) -> None:
    result = python_analysis(docs_json, operation, field)
    print(f"python_analysis ({operation}):")
    print(result)


async def main_async(query: str, role: str) -> None:
    await test_knowledge_search(query, role)

    tools = build_tools(HybridRetriever())
    search_tool = next(t for t in tools if t.name == "knowledge_search")
    raw = await search_tool.ainvoke({"query": query, "top_k": 8, "user_role": role})
    test_python_analysis(raw, "count_by_field", "document_type")
    test_python_analysis(raw, "score_summary", None)
    test_python_analysis(raw, "group_by_namespace", None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test agent tools")
    parser.add_argument("query", nargs="?", default="payment failure outage")
    parser.add_argument("--role", default="analyst")
    args = parser.parse_args()
    asyncio.run(main_async(args.query, args.role))


if __name__ == "__main__":
    main()
