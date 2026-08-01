"""Health check routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.app.api.deps import SettingsDep
from backend.app.api.schemas import HealthResponse
from backend.app.core.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep) -> HealthResponse:
    services = _check_services(settings)
    status = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    logger.info("Health check status=%s", status)
    return HealthResponse(status=status, environment=settings.app_env, services=services)


def _check_services(settings: Settings) -> dict[str, str]:
    services: dict[str, str] = {"api": "ok"}

    services["google_api_key"] = "ok" if settings.google_api_key else "missing"
    services["pinecone_api_key"] = "ok" if settings.pinecone_api_key else "missing"

    return services
