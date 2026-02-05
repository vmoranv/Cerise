"""Admin API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .abilities import router as abilities_router
from .characters import router as characters_router
from .config import router as config_router
from .memory import router as memory_router
from .plugins import router as plugins_router
from .plugins_deps import router as plugins_deps_router
from .plugins_runtime import router as plugins_runtime_router
from .providers import router as providers_router
from .security import require_admin
from .stars import router as stars_router

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
router.include_router(abilities_router)
router.include_router(config_router)
router.include_router(memory_router)
router.include_router(providers_router)
router.include_router(characters_router)
router.include_router(plugins_runtime_router)
router.include_router(plugins_deps_router)
router.include_router(plugins_router)
router.include_router(stars_router)

__all__ = ["router"]
