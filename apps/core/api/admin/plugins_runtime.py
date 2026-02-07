"""Admin plugin runtime routes (load/unload/reload + introspection)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from ...config import ConfigLoader, get_config_loader
from ...plugins.name_safety import validate_plugin_name
from ..dependencies import get_services

if TYPE_CHECKING:
    from ..container import AppServices

router = APIRouter()


def _load_star_config(plugin_name: str, *, loader: ConfigLoader, plugins_dir: Any) -> dict[str, Any]:
    plugin_dir = plugins_dir / plugin_name
    schema = loader.load_star_schema(plugin_dir) if plugin_dir.exists() else None
    return loader.load_star_config(plugin_name, schema=schema)


@router.get("/plugins/runtime")
async def list_loaded_plugins(services: AppServices = Depends(get_services)) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for name in services.plugin_manager.list_plugins():
        plugin = services.plugin_manager.get_plugin(name)
        items.append(
            {
                "name": name,
                "running": bool(plugin.is_running) if plugin else False,
            },
        )
    items.sort(key=lambda entry: entry["name"])
    return {"plugins": items}


@router.get("/plugins/{name}/runtime")
async def get_loaded_plugin(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    plugin = services.plugin_manager.get_plugin(name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not loaded")

    return {
        "name": name,
        "running": bool(plugin.is_running),
        "manifest": plugin.manifest.__dict__,
        "abilities": plugin.abilities,
    }


@router.post("/plugins/{name}/runtime/load")
async def load_plugin(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    loader = get_config_loader()
    config = _load_star_config(
        name,
        loader=loader,
        plugins_dir=services.plugin_manager.plugins_dir,
    )

    ok = await services.plugin_manager.load(name, config)
    if ok:
        await services.plugin_bridge.register_plugin_abilities()
        return {"status": "loaded"}
    raise HTTPException(status_code=400, detail="Failed to load plugin")


@router.post("/plugins/{name}/runtime/unload")
async def unload_plugin(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ok = await services.plugin_manager.unload(name)
    if ok:
        await services.plugin_bridge.register_plugin_abilities()
        return {"status": "unloaded"}
    raise HTTPException(status_code=404, detail="Plugin not loaded")


@router.post("/plugins/{name}/runtime/reload")
async def reload_plugin(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ok = await services.plugin_manager.reload(name)
    if ok:
        await services.plugin_bridge.register_plugin_abilities()
        return {"status": "reloaded"}
    raise HTTPException(status_code=400, detail="Failed to reload plugin")


@router.get("/plugins/{name}/runtime/health")
async def plugin_health(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ok = await services.plugin_manager.health_check(name)
    return {"plugin": name, "healthy": bool(ok)}
