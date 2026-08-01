"""API request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


UserRole = Literal["viewer", "analyst", "admin"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    user_role: UserRole = "viewer"
    department: str | None = None
    document_type: str | None = None


class Citation(BaseModel):
    chunk_id: str
    title: str
    source_file: str
    namespace: str
    section_heading: str = ""
    hybrid_score: float
    access_level: str | None = None
    text_preview: str = ""


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    citations: list[Citation]
    retrieval_count: int
    model: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    user_role: UserRole = "viewer"
    top_k: int = Field(default=5, ge=1, le=20)
    department: str | None = None
    document_type: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
