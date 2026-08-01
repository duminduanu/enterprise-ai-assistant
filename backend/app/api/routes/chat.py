"""Chat and search routes powered by LangGraph multi-agent orchestration."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Request
from langsmith import traceable
from sse_starlette.sse import EventSourceResponse

from backend.app.agents.runner import docs_to_hits, run_agent
from backend.app.agents.stream_runner import stream_agent
from backend.app.agents.streaming import (
    sse_agent_event,
    sse_done,
    sse_error,
    sse_node,
    sse_started,
    sse_token,
)
from backend.app.api.deps import CurrentUserDep, RateLimitDep, RetrieverDep
from backend.app.api.schemas import (
    AgentEvent,
    ChatRequest,
    ChatResponse,
    Citation,
    SearchRequest,
    SearchResponse,
)
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError, LLMError, RetrievalError, ValidationError
from backend.app.retrieval import HybridRetriever
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit
from backend.app.security.prompt_injection import check_user_input

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])


def _validate_chat_message(message: str) -> None:
    if not message.strip():
        raise ValidationError("Message cannot be empty")
    is_safe, violations = check_user_input(message)
    if not is_safe:
        raise ValidationError(f"Message blocked by security policy: {violations[0]}")


def _build_chat_response(
    *,
    result: dict,
    session_id: str,
    user_role: str,
) -> ChatResponse:
    hits = docs_to_hits(result.get("retrieved_docs") or [])
    citations = [_hit_to_citation(hit) for hit in hits]
    agent_events = [
        AgentEvent(
            node=event.get("node", ""),
            event_type=event.get("event_type", ""),
            message=event.get("message", ""),
            metadata=event.get("metadata") or {},
        )
        for event in result.get("agent_events") or []
    ]
    settings = get_settings()
    impact = result.get("butterfly_impact") or {}
    return ChatResponse(
        answer=result.get("final_answer") or "",
        session_id=session_id,
        citations=citations,
        retrieval_count=len(citations),
        model=settings.llm_model,
        route=result.get("route"),
        current_node=result.get("current_node"),
        validation_passed=result.get("validation_passed"),
        agent_events=agent_events,
        history_turns=result.get("history_turns", 0),
        user_role=user_role,
        degraded_mode=result.get("degraded_mode"),
        failure_count=len(result.get("failure_chain") or []),
        handoff_count=len(result.get("handoff_notes") or []),
        butterfly_severity=impact.get("severity"),
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: CurrentUserDep,
    _rate_limit: RateLimitDep,
) -> ChatResponse:
    """Multi-agent chat via LangGraph: supervisor -> retrieval|research -> response -> validate."""
    request_id = getattr(request.state, "request_id", "unknown")
    session_id = body.session_id or str(uuid.uuid4())
    user_role = current_user.role

    _validate_chat_message(body.message)

    try:
        result = await run_agent(
            message=body.message,
            user_role=user_role,
            session_id=session_id,
            request_id=request_id,
            department=body.department,
            document_type=body.document_type,
        )
    except AppError:
        raise
    except FileNotFoundError as exc:
        raise RetrievalError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent run failed request_id=%s", request_id)
        raise LLMError(
            "The assistant encountered an unexpected error. Please try again."
        ) from exc

    response = _build_chat_response(
        result=result,
        session_id=session_id,
        user_role=user_role,
    )

    logger.info(
        "Chat completed request_id=%s session_id=%s route=%s citations=%d",
        request_id,
        session_id,
        result.get("route"),
        response.retrieval_count,
    )

    return response


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    current_user: CurrentUserDep,
    _rate_limit: RateLimitDep,
) -> EventSourceResponse:
    """SSE stream: agent node updates, agent events, LLM tokens, and final payload."""
    request_id = getattr(request.state, "request_id", "unknown")
    session_id = body.session_id or str(uuid.uuid4())
    user_role = current_user.role

    try:
        _validate_chat_message(body.message)
    except ValidationError as exc:
        error_message = str(exc.message)

        async def validation_error_stream():
            yield sse_error(error_message, request_id=request_id)

        return EventSourceResponse(validation_error_stream())

    async def event_generator():
        yield sse_started(session_id=session_id, request_id=request_id)
        try:
            async for item in stream_agent(
                message=body.message,
                user_role=user_role,
                session_id=session_id,
                request_id=request_id,
                department=body.department,
                document_type=body.document_type,
            ):
                item_type = item.get("type")
                if item_type == "node":
                    yield sse_node(
                        node=item["node"],
                        status=item.get("status", "complete"),
                        current_node=item.get("current_node"),
                        route=item.get("route"),
                    )
                elif item_type == "agent_event":
                    yield sse_agent_event(item["event"])
                elif item_type == "token":
                    yield sse_token(item.get("content", ""))
                elif item_type == "done":
                    response = _build_chat_response(
                        result=item["result"],
                        session_id=session_id,
                        user_role=user_role,
                    )
                    yield sse_done(response.model_dump())
            logger.info(
                "Chat stream completed request_id=%s session_id=%s",
                request_id,
                session_id,
            )
        except AppError as exc:
            yield sse_error(exc.message, request_id=request_id)
        except Exception:
            logger.exception("Chat stream failed request_id=%s", request_id)
            yield sse_error(
                "The assistant encountered an unexpected error. Please try again.",
                request_id=request_id,
            )

    return EventSourceResponse(event_generator())


@router.post("/search", response_model=SearchResponse)
async def search(
    request: Request,
    body: SearchRequest,
    retriever: RetrieverDep,
    current_user: CurrentUserDep,
    _rate_limit: RateLimitDep,
) -> SearchResponse:
    """Direct hybrid search endpoint for debugging and tooling."""
    is_safe, violations = check_user_input(body.query)
    if not is_safe:
        raise ValidationError(f"Query blocked by security policy: {violations[0]}")

    request_id = getattr(request.state, "request_id", None)
    filters = RetrievalFilters(
        department=body.department,
        document_type=body.document_type,
    )
    try:
        hits = await _run_search(
            query=body.query,
            user_role=current_user.role,
            top_k=body.top_k,
            filters=filters,
            retriever=retriever,
            request_id=request_id,
        )
    except FileNotFoundError as exc:
        raise RetrievalError(str(exc)) from exc
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Search failed request_id=%s", request_id)
        raise RetrievalError("Search is temporarily unavailable") from exc
    return SearchResponse(
        query=body.query,
        results=[hit.to_dict() for hit in hits],
    )


@traceable(name="search_pipeline", run_type="chain")
async def _run_search(
    *,
    query: str,
    user_role: str,
    top_k: int | None,
    filters: RetrievalFilters,
    retriever: HybridRetriever,
    request_id: str | None,
) -> list[RetrievalHit]:
    return await retriever.asearch(
        query,
        user_role=user_role,
        top_k=top_k,
        filters=filters,
    )


def _hit_to_citation(hit: RetrievalHit) -> Citation:
    return Citation(
        chunk_id=hit.chunk_id,
        title=hit.title,
        source_file=hit.source_file,
        namespace=hit.namespace,
        section_heading=hit.section_heading,
        hybrid_score=round(hit.hybrid_score, 4),
        access_level=str(hit.metadata.get("access_level")),
        text_preview=hit.text[:300],
    )
