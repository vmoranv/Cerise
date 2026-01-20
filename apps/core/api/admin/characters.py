"""Admin character routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...config import CharacterConfig, get_config_loader

router = APIRouter()


@router.get("/characters")
async def list_characters() -> dict:
    """List available characters."""
    loader = get_config_loader()
    return {"characters": loader.list_characters()}


@router.get("/characters/{name}")
async def get_character(name: str) -> dict:
    """Get character configuration."""
    loader = get_config_loader()
    try:
        config = loader.load_character_config(name)
        return config.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Character not found") from e


@router.put("/characters/{name}")
async def update_character(name: str, config: dict) -> dict:
    """Update character configuration."""
    loader = get_config_loader()
    try:
        char_config = CharacterConfig(**config)
        loader.save_character_config(char_config, name)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
