"""Admin API routes."""

from __future__ import annotations

from fastapi import APIRouter

from .characters import router as characters_router
from .config import router as config_router
from .memory import router as memory_router
from .plugins import router as plugins_router
from .providers import router as providers_router

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(config_router)
router.include_router(memory_router)
router.include_router(providers_router)
router.include_router(characters_router)
router.include_router(plugins_router)

__all__ = ["router"]
