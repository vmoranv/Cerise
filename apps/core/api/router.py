"""API router assembly."""

from __future__ import annotations

from fastapi import APIRouter

from .routes import (
    agents_router,
    chat_router,
    emotion_router,
    health_router,
    live2d_router,
    openai_router,
    sessions_router,
    skills_router,
    websocket_router,
)

router = APIRouter()
router.include_router(health_router)
router.include_router(sessions_router)
router.include_router(agents_router)
router.include_router(skills_router)
router.include_router(chat_router)
router.include_router(emotion_router)
router.include_router(live2d_router)
router.include_router(websocket_router)
router.include_router(openai_router)
