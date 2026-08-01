"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 480
    auth_required: bool = False

    google_api_key: str = ""
    llm_model: str = "gemini-3.1-flash-lite"

    pinecone_api_key: str = ""
    pinecone_index_name: str = "enterprise-ai-assistant-gemini"

    langsmith_tracing: bool = True
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "enterprise-ai-assistant"

    hybrid_alpha: float = 0.7
    retrieval_top_k: int = 5

    session_memory_max_turns: int = 10

    rate_limit_requests_per_minute: int = 20

    llm_timeout_seconds: int = 45
    tool_timeout_seconds: int = 30
    mcp_timeout_seconds: int = 15
    agent_timeout_seconds: int = 120


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
