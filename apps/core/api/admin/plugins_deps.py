"""Admin plugin dependency install routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from ...plugins.deps_jobs import PluginDepsJobs
from ...plugins.name_safety import validate_plugin_name
from ..dependencies import get_services

if TYPE_CHECKING:
    from ..container import AppServices

router = APIRouter()


@router.post("/plugins/{name}/deps/install")
async def install_plugin_deps(
    name: str,
    force: bool = False,
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    jobs = PluginDepsJobs(store=services.state_store, plugins_dir=services.plugin_manager.plugins_dir)
    try:
        job = await jobs.start(name, force=bool(force))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@router.get("/plugins/{name}/deps/status")
async def get_plugin_deps_status(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    jobs = PluginDepsJobs(store=services.state_store, plugins_dir=services.plugin_manager.plugins_dir)
    job = await jobs.get(name)
    if not job:
        raise HTTPException(status_code=404, detail="No dependency job found")
    return {"job": job}
