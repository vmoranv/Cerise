"""Admin plugin routes."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from ...config import get_config_loader
from ...plugins.installer import PluginInstaller
from ...plugins.name_safety import validate_plugin_name
from ...plugins.plugin_types import PluginManifest
from ..dependencies import get_services
from .models import GitHubInstallRequest, PluginConfigUpdate

router = APIRouter()

logger = logging.getLogger(__name__)


def _merge_dict(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _read_manifest(manifest_path: Path) -> PluginManifest | None:
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read plugin manifest %s: %s", manifest_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    return PluginManifest.from_dict(data)


def _load_star_schema_and_config(
    *, loader, plugin_name: str, plugin_dir: Path
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    schema = loader.load_star_schema(plugin_dir) if plugin_dir.exists() else None
    config: dict[str, Any] = loader.load_star_config(plugin_name, schema=schema)
    return config, schema


async def _maybe_load_plugin(*, plugin_name: str, load: bool, services) -> bool:
    if not load:
        return False

    loader = get_config_loader()
    plugin_dir = services.plugin_manager.plugins_dir / plugin_name
    config, _schema = _load_star_schema_and_config(loader=loader, plugin_name=plugin_name, plugin_dir=plugin_dir)

    ok = await services.plugin_manager.load(plugin_name, config)
    if ok:
        await services.plugin_bridge.register_plugin_abilities()
    return bool(ok)


@router.get("/plugins")
async def list_plugins(services=Depends(get_services)) -> dict:
    """List installed + discovered plugins."""
    installer = PluginInstaller(plugins_dir=services.plugin_manager.plugins_dir)
    registered = {p.name: p for p in installer.list_installed()}

    discovered = await services.plugin_manager.discover()
    manifests = {m.name: m for m in discovered}

    loaded = set(services.plugin_manager.list_plugins())
    loader = get_config_loader()

    result: list[dict[str, Any]] = []
    for name in sorted(set(registered) | set(manifests)):
        reg = registered.get(name)
        manifest = manifests.get(name)

        if reg:
            item: dict[str, Any] = reg.model_dump()
        elif manifest:
            item = {
                "name": manifest.name,
                "version": manifest.version,
                "source": "local",
                "source_url": "",
                "enabled": True,
                "installed_at": "",
            }
        else:
            continue

        item["registered"] = reg is not None
        item["discovered"] = manifest is not None
        item["loaded"] = name in loaded

        if manifest:
            item.setdefault("display_name", manifest.display_name)
            item.setdefault("description", manifest.description)
            item.setdefault("author", manifest.author)

        star = loader.get_star_entry(name)
        item["star_enabled"] = bool(star.enabled) if star else True
        item["star_allow_tools"] = bool(star.allow_tools) if star else True

        if item["loaded"]:
            loaded_plugin = services.plugin_manager.get_plugin(name)
            item["running"] = bool(loaded_plugin.is_running) if loaded_plugin else False
        else:
            item["running"] = False

        result.append(item)

    return {"plugins": result}


@router.post("/plugins/install/github")
async def install_from_github(
    request: GitHubInstallRequest,
    load: bool = False,
    services=Depends(get_services),
) -> dict:
    """Install plugin from GitHub."""
    installer = PluginInstaller(plugins_dir=services.plugin_manager.plugins_dir)

    plugin = await installer.install_from_github(
        repo_url=request.repo_url,
        branch=request.branch,
    )

    if plugin:
        payload: dict = {"status": "installed", "plugin": plugin.model_dump()}
        if await _maybe_load_plugin(plugin_name=plugin.name, load=bool(load), services=services):
            payload["loaded"] = True
        return payload

    raise HTTPException(status_code=400, detail="Failed to install plugin")


@router.post("/plugins/install/upload")
async def install_from_upload(
    request: Request,
    load: bool = False,
    services=Depends(get_services),
) -> dict:
    """Install plugin from uploaded zip file.

    Supports:
    - Raw zip bytes in the request body (recommended): Content-Type application/zip or application/octet-stream.
      Optionally pass X-Filename header.
    - multipart/form-data with a 'file' field, if python-multipart is installed.
    """

    installer = PluginInstaller(plugins_dir=services.plugin_manager.plugins_dir)
    content_type = (request.headers.get("content-type") or "").lower()
    filename = request.headers.get("x-filename") or ""

    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Multipart uploads require python-multipart (or send raw zip bytes).",
            ) from exc

        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(status_code=400, detail="Expected form field 'file'.")
        filename = file.filename or ""
        content = await file.read()
    else:
        if not filename:
            filename = "plugin.zip"
        content = await request.body()

    if not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")
    if not content:
        raise HTTPException(status_code=400, detail="Upload is empty")

    plugin = await installer.install_from_zip_bytes(content)

    if plugin:
        payload: dict = {"status": "installed", "plugin": plugin.model_dump()}
        if await _maybe_load_plugin(plugin_name=plugin.name, load=bool(load), services=services):
            payload["loaded"] = True
        return payload

    raise HTTPException(status_code=400, detail="Failed to install plugin")


@router.delete("/plugins/{name}")
async def uninstall_plugin(name: str, services=Depends(get_services)) -> dict:
    """Uninstall a plugin."""
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    installer = PluginInstaller(plugins_dir=services.plugin_manager.plugins_dir)

    if services.plugin_manager.get_plugin(name):
        await services.plugin_manager.unload(name)
        await services.plugin_bridge.register_plugin_abilities()

    if await installer.uninstall(name):
        return {"status": "uninstalled"}

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/plugins/{name}")
async def get_plugin(name: str, services=Depends(get_services)) -> dict:
    """Get plugin info."""
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    installer = PluginInstaller(plugins_dir=services.plugin_manager.plugins_dir)
    plugin = installer.get_plugin_info(name)

    manifest = _read_manifest(services.plugin_manager.plugins_dir / name / "manifest.json")

    if not plugin and not manifest:
        raise HTTPException(status_code=404, detail="Plugin not found")

    if plugin:
        dumped: dict[str, Any] = plugin.model_dump()
    else:
        dumped = {
            "name": name,
            "version": manifest.version if manifest else "",
            "source": "local",
            "source_url": "",
            "enabled": True,
            "installed_at": "",
        }

    dumped["registered"] = plugin is not None
    dumped["discovered"] = manifest is not None
    if manifest:
        dumped["manifest"] = asdict(manifest)

    loaded_plugin = services.plugin_manager.get_plugin(name)
    dumped["loaded"] = loaded_plugin is not None
    dumped["running"] = bool(loaded_plugin.is_running) if loaded_plugin else False
    return dumped


@router.put("/plugins/{name}")
async def update_plugin_config(name: str, request: PluginConfigUpdate, services=Depends(get_services)) -> dict:
    """Update plugin configuration (enable/disable, config)."""
    try:
        name = validate_plugin_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    loader = get_config_loader()
    registry = loader.get_plugins_registry()

    for i, p in enumerate(registry.plugins):
        if p.name == name:
            if request.enabled is not None:
                registry.plugins[i].enabled = request.enabled
            loader.save_plugins_registry(registry)

            if request.config is not None:
                plugin_dir = services.plugin_manager.plugins_dir / name
                current, schema = _load_star_schema_and_config(loader=loader, plugin_name=name, plugin_dir=plugin_dir)
                merged = _merge_dict(current, request.config)
                if schema:
                    merged, _changed = loader.apply_star_schema(schema, merged)
                    errors = loader.validate_star_config(merged, schema)
                    if errors:
                        raise HTTPException(status_code=400, detail={"errors": errors})
                loader.save_star_config(name, merged)
                return {"status": "updated", "config": merged}

            return {"status": "updated"}

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.post("/plugins/{name}/enable")
async def enable_plugin(name: str, services=Depends(get_services)) -> dict:
    """Enable a plugin."""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=True), services)


@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str, services=Depends(get_services)) -> dict:
    """Disable a plugin."""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=False), services)
