"""Prompt injection detection and untrusted document wrapping."""

from __future__ import annotations

import re

# Patterns commonly used to hijack LLM behavior (case-insensitive).
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
        r"disregard\s+(all\s+)?(previous|prior|above)",
        r"forget\s+(all\s+)?(previous|prior|your)\s+instructions",
        r"you\s+are\s+now",
        r"new\s+instructions\s*:",
        r"system\s+prompt",
        r"reveal\s+(your\s+)?(instructions|prompt|system)",
        r"override\s+(safety|security|guardrails?)",
        r"developer\s+mode",
        r"jailbreak",
        r"<\s*/?\s*system\s*>",
        r"assistant\s*:\s*",
        r"do\s+not\s+follow\s+(the\s+)?(above|bank|enterprise)",
    )
)

UNTRUSTED_DOC_START = "<<<UNTRUSTED_RETRIEVED_DOCUMENT>>>"
UNTRUSTED_DOC_END = "<<<END_UNTRUSTED_RETRIEVED_DOCUMENT>>>"


def check_user_input(text: str) -> tuple[bool, list[str]]:
    """
    Return (is_safe, violations).

    Safe input has no blocklisted injection patterns.
    """
    violations: list[str] = []
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append(f"Blocked pattern: {match.group(0)[:80]}")
    return len(violations) == 0, violations


def wrap_untrusted_document(text: str, *, source_file: str, title: str) -> str:
    """Wrap retrieved content so the LLM treats it as untrusted data, not instructions."""
    body = text.strip()
    return (
        f"{UNTRUSTED_DOC_START}\n"
        f"source={source_file}\n"
        f"title={title}\n"
        f"---\n"
        f"{body}\n"
        f"{UNTRUSTED_DOC_END}"
    )
