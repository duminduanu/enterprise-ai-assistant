"""In-memory conversational session store (last N turns per session)."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from backend.app.core.config import get_settings

Role = Literal["user", "assistant"]

FOLLOW_UP_PATTERNS = (
    r"\bit\b",
    r"\bthat\b",
    r"\bthis\b",
    r"\bthose\b",
    r"\bthey\b",
    r"\bthe same\b",
    r"\bwhat about\b",
    r"\balso\b",
    r"\bmore detail\b",
    r"\btell me more\b",
    r"\bexpand on\b",
)


@dataclass
class ChatTurn:
    role: Role
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class SessionMemoryStore:
    """Thread-safe in-memory store of recent chat turns keyed by session_id."""

    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max(1, max_turns)
        self._sessions: dict[str, list[ChatTurn]] = {}
        self._lock = asyncio.Lock()

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        async with self._lock:
            turns = self._sessions.get(session_id, [])
            return [turn.to_dict() for turn in turns]

    async def append_turn(self, session_id: str, role: Role, content: str) -> None:
        if not content.strip():
            return
        async with self._lock:
            turns = self._sessions.setdefault(session_id, [])
            turns.append(ChatTurn(role=role, content=content.strip()))
            max_messages = self._max_turns * 2
            if len(turns) > max_messages:
                self._sessions[session_id] = turns[-max_messages:]

    async def clear_session(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def session_count(self) -> int:
        async with self._lock:
            return len(self._sessions)


def is_follow_up_question(question: str) -> bool:
    lowered = question.lower().strip()
    return any(re.search(pattern, lowered) for pattern in FOLLOW_UP_PATTERNS)


def format_history_for_prompt(
    history: list[dict[str, str]],
    *,
    max_turns: int = 5,
) -> str:
    if not history:
        return ""

    recent = history[-(max_turns * 2) :]
    lines = []
    for turn in recent:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def contextualize_question(question: str, history: list[dict[str, str]]) -> str:
    """Expand short follow-ups with recent conversation context for retrieval."""
    if not history or not is_follow_up_question(question):
        return question

    recent = history[-4:]
    context_lines = format_history_for_prompt(recent, max_turns=2)
    return (
        f"Conversation context:\n{context_lines}\n\n"
        f"Follow-up question: {question}"
    )


@lru_cache(maxsize=1)
def get_session_store() -> SessionMemoryStore:
    settings = get_settings()
    return SessionMemoryStore(max_turns=settings.session_memory_max_turns)
