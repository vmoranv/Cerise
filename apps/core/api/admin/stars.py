"""Admin star config routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...config import get_config_loader
from ...config.schemas import StarAbilityToggle, StarEntry
from .models import StarAbilityUpdate, StarConfigUpdate, StarConfigValidate, StarEntryUpdate

router = APIRouter()


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _load_schema(loader: Any, plugin_name: str) -> dict[str, Any] | None:
    plugin_dir = loader.get_plugins_dir() / plugin_name
    if not plugin_dir.exists():
        return None
    schema = loader.load_star_schema(plugin_dir)
    if isinstance(schema, dict):
        return schema
    return None


def _get_or_create_entry(loader: Any, plugin_name: str) -> StarEntry:
    entry = loader.get_star_entry(plugin_name)
    if isinstance(entry, StarEntry):
        return entry
    return StarEntry(name=plugin_name)


@router.get("/stars")
async def list_stars() -> dict[str, Any]:
    """List star registry entries."""
    loader = get_config_loader()
    registry = loader.get_plugins_registry()
    star_registry = loader.get_star_registry()
    stars = []
    for plugin in registry.plugins:
        entry = star_registry.get_star(plugin.name) or StarEntry(name=plugin.name)
        schema = _load_schema(loader, plugin.name)
        stars.append(
            {
                **entry.model_dump(),
                "has_schema": bool(schema),
            }
        )
    return {"stars": stars}


@router.get("/stars/{name}")
async def get_star(name: str) -> dict[str, Any]:
    """Get star entry and config."""
    loader = get_config_loader()
    entry = _get_or_create_entry(loader, name)
    schema = _load_schema(loader, name)
    config = loader.load_star_config(name, schema=schema)
    return {
        "entry": entry.model_dump(),
        "config": config,
        "has_schema": bool(schema),
    }


@router.put("/stars/{name}")
async def update_star_entry(name: str, request: StarEntryUpdate) -> dict[str, Any]:
    """Update star entry toggles."""
    loader = get_config_loader()
    entry = _get_or_create_entry(loader, name)
    if request.enabled is not None:
        entry.enabled = request.enabled
    if request.allow_tools is not None:
        entry.allow_tools = request.allow_tools
    loader.upsert_star_entry(entry)
    return {"status": "updated", "entry": entry.model_dump()}


@router.put("/stars/{name}/abilities/{ability}")
async def update_star_ability(name: str, ability: str, request: StarAbilityUpdate) -> dict[str, Any]:
    """Update star ability toggles."""
    loader = get_config_loader()
    entry = _get_or_create_entry(loader, name)
    toggle = entry.abilities.get(ability) or StarAbilityToggle()
    if request.enabled is not None:
        toggle.enabled = request.enabled
    if request.allow_tools is not None:
        toggle.allow_tools = request.allow_tools
    entry.abilities[ability] = toggle
    loader.upsert_star_entry(entry)
    return {"status": "updated", "entry": entry.model_dump()}


@router.get("/stars/{name}/schema")
async def get_star_schema(name: str) -> dict[str, Any]:
    """Get star config schema."""
    loader = get_config_loader()
    schema = _load_schema(loader, name)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema


@router.get("/stars/{name}/config")
async def get_star_config(name: str) -> dict[str, Any]:
    """Get star config data."""
    loader = get_config_loader()
    schema = _load_schema(loader, name)
    config = loader.load_star_config(name, schema=schema)
    return {"config": config}


@router.put("/stars/{name}/config")
async def update_star_config(name: str, request: StarConfigUpdate) -> dict[str, Any]:
    """Update star config data."""
    loader = get_config_loader()
    schema = _load_schema(loader, name)
    current = loader.load_star_config(name, schema=schema)
    merged = _merge_dict(current, request.config)
    if schema:
        merged, _ = loader.apply_star_schema(schema, merged)
        errors = loader.validate_star_config(merged, schema)
        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})
    loader.save_star_config(name, merged)
    return {"status": "updated", "config": merged}


@router.post("/stars/{name}/config/validate")
async def validate_star_config(name: str, request: StarConfigValidate) -> dict[str, Any]:
    """Validate star config data."""
    loader = get_config_loader()
    schema = _load_schema(loader, name)
    if not schema:
        return {"valid": True, "errors": []}
    config = request.config
    if config is None:
        config = loader.load_star_config(name, schema=schema)
    errors = loader.validate_star_config(config, schema)
    return {"valid": not errors, "errors": errors}
