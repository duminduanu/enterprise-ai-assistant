"""Output guardrails: citations, brand safety, tool authorization audit."""

from __future__ import annotations

import re
from typing import Any

from backend.app.security.rbac import can_use_tool

CITATION_PATTERN = re.compile(r"\[source:\s*([^\]]+)\]", re.IGNORECASE)

OUTPUT_INJECTION_MARKERS = (
    "ignore previous instructions",
    "system prompt",
    "you are now",
    "developer mode",
)

BRAND_UNSAFE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bcompetitor\s+bank\b",
        r"\b(?:hsbc|barclays|citibank|jpmorgan)\b",
        r"\bnot\s+affiliated\s+with\s+commercial\s+bank\b",
        r"\bunofficial\s+advice\b",
    )
)


def _known_sources(docs: list[dict[str, Any]]) -> set[str]:
    return {doc.get("source_file", "") for doc in docs if doc.get("source_file")}


def _citation_matches_known(citation: str, known: set[str]) -> bool:
    cite = citation.strip()
    if not cite:
        return False
    if cite in known:
        return True
    return any(
        cite in source or source.endswith(cite) or cite.endswith(source)
        for source in known
    )


def find_hallucinated_citations(answer: str, docs: list[dict[str, Any]]) -> list[str]:
    """Flag [source: ...] citations that do not map to retrieved documents."""
    known = _known_sources(docs)
    if not known:
        return []

    issues: list[str] = []
    for raw in CITATION_PATTERN.findall(answer):
        if not _citation_matches_known(raw, known):
            issues.append(f"Hallucinated citation: {raw.strip()}")
    return issues


def find_brand_violations(answer: str) -> list[str]:
    issues: list[str] = []
    for pattern in BRAND_UNSAFE_PATTERNS:
        match = pattern.search(answer)
        if match:
            issues.append(f"Brand safety: disallowed phrasing ({match.group(0)[:60]})")
    return issues


def find_unauthorized_tool_calls(
    tool_calls: list[dict[str, Any]] | None,
    user_role: str,
) -> list[str]:
    issues: list[str] = []
    for call in tool_calls or []:
        tool_name = call.get("tool") or call.get("name")
        if not tool_name:
            continue
        if not can_use_tool(user_role, str(tool_name)):
            issues.append(f"Unauthorized tool invocation logged: {tool_name}")
    return issues


def validate_answer_guardrails(
    answer: str,
    docs: list[dict[str, Any]],
    *,
    user_role: str = "viewer",
    tool_calls: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Run all post-generation guardrail checks; return human-readable issues."""
    issues: list[str] = []
    lowered = answer.lower()

    if not docs and "do not have enough information" not in lowered:
        if "retrieval-only response" not in lowered:
            issues.append("No retrieved documents but answer did not admit insufficient context")

    if docs:
        cited_any = any(
            doc.get("source_file", "") in answer for doc in docs if doc.get("source_file")
        )
        if not cited_any and "retrieval-only response" not in lowered:
            issues.append("Answer missing inline source citations")
        issues.extend(find_hallucinated_citations(answer, docs))

    if any(marker in lowered for marker in OUTPUT_INJECTION_MARKERS):
        issues.append("Potential prompt-injection phrasing detected in output")

    issues.extend(find_brand_violations(answer))
    issues.extend(find_unauthorized_tool_calls(tool_calls, user_role))
    return issues
