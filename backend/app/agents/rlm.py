"""RLM (Recursive Language Model) batch decomposition for complex research queries."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from backend.app.agents.events import make_event
from backend.app.agents.prompts import (
    RLM_AGGREGATE_PROMPT,
    RLM_BATCH_ANALYSIS_PROMPT,
    RLM_PLAN_PROMPT,
)
from backend.app.agents.state import AgentState
from backend.app.llm.provider import get_chat_llm
from backend.app.observability.langsmith_config import build_run_config
from backend.app.retrieval import HybridRetriever
from backend.app.retrieval.schemas import RetrievalFilters, RetrievalHit

logger = logging.getLogger(__name__)


@dataclass
class ResearchBatch:
    batch_id: str
    query: str
    focus: str


@dataclass
class ResearchPlan:
    objective: str
    batches: list[ResearchBatch]


@dataclass
class BatchResult:
    batch: ResearchBatch
    docs: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


@dataclass
class RLMResult:
    plan: ResearchPlan
    batch_results: list[BatchResult]
    retrieved_docs: list[dict[str, Any]]
    research_notes: str
    agent_events: list[dict[str, Any]]


@traceable(name="rlm_pipeline", run_type="chain")
async def run_rlm_pipeline(
    *,
    question: str,
    state: AgentState,
    retriever: HybridRetriever,
) -> RLMResult:
    """Execute plan -> batch retrieve -> batch analyze -> aggregate."""
    events: list[dict[str, Any]] = []

    plan = await _generate_plan(question, state)
    events.append(
        make_event(
            "research",
            "rlm_plan_created",
            f"RLM plan with {len(plan.batches)} batches",
            objective=plan.objective,
            batches=[{"id": b.batch_id, "query": b.query, "focus": b.focus} for b in plan.batches],
        )
    )

    batch_results: list[BatchResult] = []
    merged: dict[str, dict[str, Any]] = {}

    for batch in plan.batches:
        events.append(
            make_event(
                "research",
                "rlm_batch_started",
                f"Processing batch {batch.batch_id}: {batch.focus}",
                batch_id=batch.batch_id,
                query=batch.query,
            )
        )

        hits = await _search_batch(batch.query, state, retriever)
        docs = _hits_to_docs(hits)

        for doc in docs:
            chunk_id = doc.get("chunk_id", "")
            existing = merged.get(chunk_id)
            if existing is None or doc.get("hybrid_score", 0) > existing.get("hybrid_score", 0):
                merged[chunk_id] = doc

        events.append(
            make_event(
                "research",
                "rlm_batch_retrieved",
                f"Batch {batch.batch_id} retrieved {len(docs)} chunks",
                batch_id=batch.batch_id,
                sources=[d.get("source_file") for d in docs[:5]],
            )
        )

        summary = await _analyze_batch(batch, docs, question, state)
        batch_results.append(BatchResult(batch=batch, docs=docs, summary=summary))

        events.append(
            make_event(
                "research",
                "rlm_batch_analyzed",
                f"Batch {batch.batch_id} analysis complete",
                batch_id=batch.batch_id,
                summary_preview=summary[:200],
            )
        )

    ranked_docs = sorted(
        merged.values(),
        key=lambda d: d.get("hybrid_score", 0),
        reverse=True,
    )[:12]

    research_notes = await _aggregate_summaries(batch_results, question, state)
    events.append(
        make_event(
            "research",
            "rlm_aggregation_complete",
            "Aggregated batch summaries into research notes",
            batch_count=len(batch_results),
            total_chunks=len(ranked_docs),
        )
    )

    return RLMResult(
        plan=plan,
        batch_results=batch_results,
        retrieved_docs=ranked_docs,
        research_notes=research_notes,
        agent_events=events,
    )


async def _generate_plan(question: str, state: AgentState) -> ResearchPlan:
    defaults = _default_plan(question)
    llm = get_chat_llm()
    run_config = build_run_config(
        run_name="rlm_planning",
        request_id=state.get("request_id"),
        session_id=state.get("session_id"),
        user_role=state.get("user_role"),
        tags=["agent", "research", "rlm"],
    )

    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [
                SystemMessage(content=RLM_PLAN_PROMPT),
                HumanMessage(content=f"Question: {question}"),
            ],
            config=run_config,
        )
        parsed = _parse_json(str(response.content))
        return _plan_from_dict(parsed, question, defaults)
    except Exception:
        logger.warning("RLM plan LLM failed; using heuristic plan")
        return defaults


async def _analyze_batch(
    batch: ResearchBatch,
    docs: list[dict[str, Any]],
    question: str,
    state: AgentState,
) -> str:
    if not docs:
        return f"No documents found for batch '{batch.focus}'."

    context = _format_batch_context(docs)
    llm = get_chat_llm()
    run_config = build_run_config(
        run_name="rlm_batch_analysis",
        request_id=state.get("request_id"),
        session_id=state.get("session_id"),
        user_role=state.get("user_role"),
        tags=["agent", "research", "rlm", "batch"],
        metadata={"batch_id": batch.batch_id},
    )

    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [
                SystemMessage(content=RLM_BATCH_ANALYSIS_PROMPT),
                HumanMessage(
                    content=(
                        f"Original question: {question}\n"
                        f"Batch focus: {batch.focus}\n"
                        f"Batch query: {batch.query}\n\n"
                        f"Retrieved context:\n{context}\n\n"
                        "Write a concise partial summary for this batch:"
                    )
                ),
            ],
            config=run_config,
        )
        summary = str(response.content).strip()
        if summary:
            return summary
    except Exception:
        logger.warning("RLM batch analysis LLM failed for %s; using heuristic", batch.batch_id)

    return _heuristic_batch_summary(batch, docs)


async def _aggregate_summaries(
    batch_results: list[BatchResult],
    question: str,
    state: AgentState,
) -> str:
    partials = "\n\n".join(
        f"[{r.batch.batch_id} — {r.batch.focus}]\n{r.summary}"
        for r in batch_results
    )

    llm = get_chat_llm()
    run_config = build_run_config(
        run_name="rlm_aggregation",
        request_id=state.get("request_id"),
        session_id=state.get("session_id"),
        user_role=state.get("user_role"),
        tags=["agent", "research", "rlm", "aggregate"],
    )

    try:
        response = await asyncio.to_thread(
            llm.invoke,
            [
                SystemMessage(content=RLM_AGGREGATE_PROMPT),
                HumanMessage(
                    content=(
                        f"Original question: {question}\n\n"
                        f"Partial batch summaries:\n{partials}\n\n"
                        "Aggregated research notes:"
                    )
                ),
            ],
            config=run_config,
        )
        notes = str(response.content).strip()
        if notes:
            return notes
    except Exception:
        logger.warning("RLM aggregation LLM failed; using heuristic merge")

    return _heuristic_aggregate(batch_results)


def _default_plan(question: str) -> ResearchPlan:
    base = question.strip()
    lowered = base.lower()

    batches = [
        ResearchBatch("batch_incidents", f"{base} incident reports", "incident reports"),
        ResearchBatch("batch_runbooks", f"{base} runbooks remediation", "runbooks and remediation"),
        ResearchBatch("batch_policies", f"{base} policies architecture", "policies and architecture"),
    ]

    if "payment" in lowered or "outage" in lowered:
        batches = [
            ResearchBatch(
                "batch_payment_incidents",
                "payment failure outage incident reports",
                "payment outage incidents",
            ),
            ResearchBatch(
                "batch_payment_runbooks",
                "payment gateway timeout runbook recovery",
                "payment recovery runbooks",
            ),
            ResearchBatch(
                "batch_payment_meetings",
                "payment reliability review meeting notes PIR",
                "post-incident reviews and meeting notes",
            ),
        ]

    return ResearchPlan(
        objective=f"Multi-batch research for: {base}",
        batches=batches,
    )


def _plan_from_dict(
    parsed: dict[str, Any],
    question: str,
    fallback: ResearchPlan,
) -> ResearchPlan:
    objective = parsed.get("objective") or fallback.objective
    raw_batches = parsed.get("batches") or parsed.get("sub_queries")

    if not raw_batches:
        return fallback

    batches: list[ResearchBatch] = []
    for i, item in enumerate(raw_batches[:4]):
        if isinstance(item, str):
            batches.append(
                ResearchBatch(f"batch_{i + 1}", item.strip(), f"focus area {i + 1}")
            )
        elif isinstance(item, dict):
            query = str(item.get("query") or item.get("sub_query") or "").strip()
            if not query:
                continue
            batches.append(
                ResearchBatch(
                    str(item.get("id") or f"batch_{i + 1}"),
                    query,
                    str(item.get("focus") or item.get("label") or f"batch {i + 1}"),
                )
            )

    if not batches:
        return fallback

    return ResearchPlan(objective=objective, batches=batches)


async def _search_batch(
    query: str,
    state: AgentState,
    retriever: HybridRetriever,
) -> list[RetrievalHit]:
    filters = RetrievalFilters(
        department=state.get("department"),
        document_type=state.get("document_type"),
    )
    return await retriever.asearch(
        query,
        user_role=state.get("user_role", "viewer"),
        top_k=4,
        filters=filters,
    )


def _hits_to_docs(hits: list[RetrievalHit]) -> list[dict[str, Any]]:
    docs = []
    for hit in hits:
        doc = hit.to_dict()
        doc["text"] = hit.text
        docs.append(doc)
    return docs


def _format_batch_context(docs: list[dict[str, Any]]) -> str:
    blocks = []
    for i, doc in enumerate(docs, start=1):
        blocks.append(
            f"[{i}] source={doc.get('source_file')} title={doc.get('title')}\n"
            f"{doc.get('text') or doc.get('text_preview', '')}"
        )
    return "\n\n".join(blocks)


def _heuristic_batch_summary(batch: ResearchBatch, docs: list[dict[str, Any]]) -> str:
    sources = list(dict.fromkeys(d.get("source_file", "") for d in docs if d.get("source_file")))
    titles = [d.get("title", "") for d in docs[:3]]
    return (
        f"Batch '{batch.focus}' ({batch.query}): retrieved {len(docs)} chunks. "
        f"Sources: {', '.join(sources[:4])}. "
        f"Key documents: {'; '.join(t for t in titles if t)}."
    )


def _heuristic_aggregate(batch_results: list[BatchResult]) -> str:
    lines = ["Aggregated RLM research notes (heuristic merge):"]
    for result in batch_results:
        lines.append(f"- {result.batch.focus}: {result.summary}")
    return "\n".join(lines)


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)
