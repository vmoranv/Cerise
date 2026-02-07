"""Admin config routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...config import AppConfig, get_config_loader
from .models import ConfigUpdateRequest

router = APIRouter()


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current application configuration."""
    loader = get_config_loader()
    config = loader.get_app_config()
    return config.model_dump()


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> dict[str, Any]:
    """Update application configuration."""
    loader = get_config_loader()

    try:
        current = loader.get_app_config().model_dump()
        current.update(request.config)
        new_config = AppConfig(**current)
        loader.save_app_config(new_config)
        return {"status": "updated", "config": new_config.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
