"""Aggregate API routers."""

from fastapi import APIRouter

from backend.app.api.routes import auth, chat, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
