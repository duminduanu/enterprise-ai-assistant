"""python_analysis tool — safe pandas summaries on retrieved JSON records."""

from __future__ import annotations

import json
from typing import Any, Callable

import pandas as pd
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

ALLOWED_OPERATIONS = frozenset(
    {
        "count_by_field",
        "list_unique_sources",
        "score_summary",
        "group_by_namespace",
    }
)


class PythonAnalysisInput(BaseModel):
    records_json: str = Field(..., description="JSON array of retrieved document records")
    operation: str = Field(
        ...,
        description=(
            "Analysis operation: count_by_field, list_unique_sources, "
            "score_summary, or group_by_namespace"
        ),
    )
    field: str | None = Field(
        default=None,
        description="Field name for count_by_field (e.g. document_type, namespace, department)",
    )


def _count_by_field(df: pd.DataFrame, field: str | None) -> dict[str, Any]:
    if not field:
        return {"error": "field is required for count_by_field"}
    if field not in df.columns:
        return {"error": f"Unknown field '{field}'. Available: {list(df.columns)}"}
    counts = df[field].fillna("unknown").value_counts().to_dict()
    return {"field": field, "counts": counts, "total": int(len(df))}


def _list_unique_sources(df: pd.DataFrame, _field: str | None) -> dict[str, Any]:
    if "source_file" not in df.columns:
        return {"error": "source_file column missing from records"}
    sources = sorted(df["source_file"].dropna().unique().tolist())
    return {"unique_source_count": len(sources), "sources": sources}


def _score_summary(df: pd.DataFrame, _field: str | None) -> dict[str, Any]:
    if "hybrid_score" not in df.columns:
        return {"error": "hybrid_score column missing from records"}
    scores = pd.to_numeric(df["hybrid_score"], errors="coerce").dropna()
    if scores.empty:
        return {"error": "No numeric hybrid_score values"}
    return {
        "count": int(len(scores)),
        "min": round(float(scores.min()), 4),
        "max": round(float(scores.max()), 4),
        "mean": round(float(scores.mean()), 4),
    }


def _group_by_namespace(df: pd.DataFrame, _field: str | None) -> dict[str, Any]:
    if "namespace" not in df.columns:
        return {"error": "namespace column missing from records"}
    grouped = df["namespace"].fillna("unknown").value_counts().to_dict()
    return {"namespace_counts": grouped, "total": int(len(df))}


_OPERATION_HANDLERS: dict[str, Callable[[pd.DataFrame, str | None], dict[str, Any]]] = {
    "count_by_field": _count_by_field,
    "list_unique_sources": _list_unique_sources,
    "score_summary": _score_summary,
    "group_by_namespace": _group_by_namespace,
}


def python_analysis(
    records_json: str,
    operation: str,
    field: str | None = None,
) -> str:
    """
    Run a predefined pandas analysis on retrieved document records.

    No arbitrary code execution — only whitelisted operations are permitted.
    """
    if operation not in ALLOWED_OPERATIONS:
        return json.dumps(
            {
                "error": f"Operation '{operation}' not allowed",
                "allowed_operations": sorted(ALLOWED_OPERATIONS),
            }
        )

    try:
        records = json.loads(records_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"Invalid JSON: {exc}"})

    if not isinstance(records, list):
        return json.dumps({"error": "records_json must be a JSON array"})

    if not records:
        return json.dumps({"error": "No records to analyze"})

    df = pd.DataFrame(records)
    handler = _OPERATION_HANDLERS[operation]
    result = handler(df, field)
    return json.dumps(result, indent=2)


def create_python_analysis_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=python_analysis,
        name="python_analysis",
        description=(
            "Analyze retrieved document records with safe pandas operations. "
            "Use for counts, grouping, score summaries — not general Python execution."
        ),
        args_schema=PythonAnalysisInput,
    )
