"""User-facing fallback messages for degraded service paths."""

from __future__ import annotations


def retrieval_failed_message(reason: str = "") -> str:
    suffix = f" ({reason})" if reason else ""
    return (
        "Knowledge base search is temporarily unavailable"
        f"{suffix}. Please try again shortly."
    )


def sparse_only_notice() -> str:
    return (
        "[Note: vector search unavailable — results may be keyword-only and less complete.]"
    )


def llm_unavailable_answer(question: str, docs: list[dict]) -> str:
    if not docs:
        return (
            "I could not find relevant information in the knowledge base, and answer synthesis "
            "is temporarily unavailable. Please try again later."
        )

    lines = [
        "Answer synthesis is temporarily unavailable. Here are the top matching sources:",
    ]
    for i, doc in enumerate(docs[:3], start=1):
        lines.append(
            f"{i}. [{doc.get('source_file')}] {doc.get('title')} — "
            f"{doc.get('section_heading', '')}"
        )
    lines.append(f"\nQuestion received: {question}")
    return "\n".join(lines)


def mcp_failure_payload(tool_name: str, reason: str) -> str:
    return (
        f'{{"error": "Enterprise lookup unavailable for {tool_name}", '
        f'"detail": "{reason}", "fallback": "continue_without_mcp"}}'
    )


def tool_failure_payload(tool_name: str, reason: str) -> str:
    return (
        f'{{"error": "Tool {tool_name} failed", '
        f'"detail": "{reason}", "fallback": "continue_without_tool"}}'
    )


def agent_timeout_answer() -> str:
    return (
        "Your request timed out before a full answer could be composed. "
        "Try a narrower question or retry in a moment."
    )
