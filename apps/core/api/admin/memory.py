"""Admin memory config routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...ai.memory.config import build_memory_config, config_to_dict, load_memory_config, save_memory_config
from ...ai.memory.time_utils import set_default_timezone
from .models import MemoryConfigUpdateRequest

router = APIRouter()


@router.get("/memory-config")
async def get_memory_config() -> dict:
    """Get current memory configuration."""
    config = load_memory_config()
    return config_to_dict(config)


@router.put("/memory-config")
async def update_memory_config(request: MemoryConfigUpdateRequest) -> dict:
    """Update memory configuration."""
    try:
        current = load_memory_config()
        updated = build_memory_config(request.config, defaults=current)
        save_memory_config(updated)
        set_default_timezone(updated.time.timezone)
        return {"status": "updated", "config": config_to_dict(updated)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
