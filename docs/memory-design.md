# Session Memory Design

## Overview

The enterprise AI assistant maintains **short-term conversational memory** per `session_id` so multi-turn chats preserve context across requests. Memory is stored in-process for the POC; production would swap the backend for Redis or a database without changing agent node contracts.

## Storage

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `SessionMemoryStore` | `backend/app/memory/session_store.py` | In-memory dict keyed by `session_id` |
| Config | `SESSION_MEMORY_MAX_TURNS` (default 10) | Max user+assistant **pairs** retained |
| Lifecycle | `run_agent()` in `backend/app/agents/runner.py` | Load before graph, append after response |

Each session stores a list of `ChatTurn` objects:

```json
{"role": "user"|"assistant", "content": "...", "timestamp": "ISO-8601"}
```

When the buffer exceeds `max_turns * 2` messages, oldest turns are dropped (FIFO).

## Data flow

```
POST /api/v1/chat (session_id)
    → SessionMemoryStore.get_history(session_id)
    → AgentState.chat_history + LangChain messages
    → LangGraph nodes (supervisor, retrieval, response)
    → SessionMemoryStore.append_turn(user + assistant)
```

## Where history is used

| Node | Usage |
|------|--------|
| **Supervisor** | Prior turns included in routing prompt for follow-up intent |
| **Retrieval** | Follow-up questions (`it`, `that`, `what about`) expand into contextualized search queries |
| **Response** | Recent conversation appended so answers reference prior turns |

Follow-up detection uses lightweight regex heuristics (`is_follow_up_question`) rather than an extra LLM call.

## API contract

Clients should reuse `session_id` from the first `ChatResponse` on subsequent turns:

```json
{"message": "What is the password reset policy?", "user_role": "analyst"}
→ {"session_id": "abc-123", "history_turns": 0, ...}

{"message": "What are the requirements for it?", "session_id": "abc-123"}
→ {"history_turns": 2, ...}
```

`history_turns` reports how many stored turns existed **before** the current request.

## Production considerations

- **Persistence**: Replace in-memory store with Redis (`HSET session:{id}`) or Postgres JSONB column.
- **TTL**: Expire idle sessions after 24h in production.
- **Privacy**: Encrypt at rest; honor data-retention policies for HR/security content.
- **Summarization**: For long sessions, compress older turns with an LLM summary node (future enhancement).
- **Horizontal scale**: Sticky sessions or shared Redis required when running multiple API replicas.

## Out of scope (POC)

- Cross-session user memory (long-term profile)
- Vector memory of past conversations
- Memory injection from retrieved documents beyond the current turn
