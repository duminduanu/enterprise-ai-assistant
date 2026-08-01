#!/usr/bin/env python3
"""Test hybrid retrieval (dense + BM25) from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.retrieval import HybridRetriever, RetrievalFilters  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Test hybrid retrieval")
    parser.add_argument("query", nargs="?", default="payment failure outage")
    parser.add_argument("--role", default="viewer", choices=["viewer", "analyst", "admin"])
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--department", default=None)
    parser.add_argument("--document-type", default=None)
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--alpha", type=float, default=None, help="Dense weight (0-1)")
    args = parser.parse_args()

    filters = RetrievalFilters(
        department=args.department,
        document_type=args.document_type,
        namespace=args.namespace,
    )

    retriever = HybridRetriever()
    hits = retriever.search(
        args.query,
        user_role=args.role,
        top_k=args.top_k,
        filters=filters,
        alpha=args.alpha,
    )

    print(f"\nQuery: {args.query}")
    print(f"Role: {args.role} | Results: {len(hits)}\n")
    for i, hit in enumerate(hits, start=1):
        print(f"--- Result {i} (hybrid={hit.hybrid_score:.4f}) ---")
        print(json.dumps(hit.to_dict(), indent=2))
        print()


if __name__ == "__main__":
    main()
