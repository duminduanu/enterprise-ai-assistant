"""OpenAPI customization for Swagger UI (documentation only; no runtime auth change)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

BEARER_SCHEME_NAME = "BearerAuth"

# Endpoints that do not require JWT in Swagger (runtime may still accept optional Bearer).
PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/api/v1/auth/login",
    }
)


def configure_swagger_auth(app: FastAPI) -> None:
    """
    Register a global Swagger **Authorize** button for JWT Bearer tokens.

    Does not change request handling — ``get_current_user`` in deps.py still
    reads the ``Authorization`` header the same way (Streamlit unchanged).
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        components = openapi_schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes[BEARER_SCHEME_NAME] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Obtain a token from **POST /api/v1/auth/login**. "
                "In Authorize, paste only the `access_token` value — "
                "Swagger adds the `Bearer` prefix automatically."
            ),
        }

        for path, path_item in openapi_schema.get("paths", {}).items():
            if path in PUBLIC_PATHS:
                continue
            for method, operation in path_item.items():
                if method.startswith("x-") or not isinstance(operation, dict):
                    continue
                operation["security"] = [{BEARER_SCHEME_NAME: []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
