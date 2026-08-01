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


class AgentEvent(BaseModel):
    node: str
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    citations: list[Citation]
    retrieval_count: int
    model: str
    route: str | None = None
    current_node: str | None = None
    validation_passed: bool | None = None
    agent_events: list[AgentEvent] = Field(default_factory=list)
    history_turns: int = 0
    user_role: UserRole | None = None


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


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    email: str
    display_name: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    role: UserRole
    display_name: str
