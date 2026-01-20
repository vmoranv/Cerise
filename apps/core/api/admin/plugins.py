"""Admin plugin routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ...config import get_config_loader
from ...plugins.installer import PluginInstaller
from .models import GitHubInstallRequest, PluginConfigUpdate

router = APIRouter()


@router.get("/plugins")
async def list_plugins() -> dict:
    """List installed plugins."""
    installer = PluginInstaller()
    plugins = installer.list_installed()
    return {"plugins": [p.model_dump() for p in plugins]}


@router.post("/plugins/install/github")
async def install_from_github(request: GitHubInstallRequest) -> dict:
    """Install plugin from GitHub."""
    installer = PluginInstaller()

    plugin = await installer.install_from_github(
        repo_url=request.repo_url,
        branch=request.branch,
    )

    if plugin:
        return {"status": "installed", "plugin": plugin.model_dump()}

    raise HTTPException(status_code=400, detail="Failed to install plugin")


@router.post("/plugins/install/upload")
async def install_from_upload(file: UploadFile = File(...)) -> dict:
    """Install plugin from uploaded zip file."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    installer = PluginInstaller()
    content = await file.read()

    plugin = await installer.install_from_zip_bytes(content)

    if plugin:
        return {"status": "installed", "plugin": plugin.model_dump()}

    raise HTTPException(status_code=400, detail="Failed to install plugin")


@router.delete("/plugins/{name}")
async def uninstall_plugin(name: str) -> dict:
    """Uninstall a plugin."""
    installer = PluginInstaller()

    if await installer.uninstall(name):
        return {"status": "uninstalled"}

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/plugins/{name}")
async def get_plugin(name: str) -> dict:
    """Get plugin info."""
    installer = PluginInstaller()
    plugin = installer.get_plugin_info(name)

    if plugin:
        return plugin.model_dump()

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.put("/plugins/{name}")
async def update_plugin_config(name: str, request: PluginConfigUpdate) -> dict:
    """Update plugin configuration (enable/disable, config)."""
    loader = get_config_loader()
    registry = loader.get_plugins_registry()

    for i, p in enumerate(registry.plugins):
        if p.name == name:
            if request.enabled is not None:
                registry.plugins[i].enabled = request.enabled
            loader.save_plugins_registry(registry)
            return {"status": "updated"}

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.post("/plugins/{name}/enable")
async def enable_plugin(name: str) -> dict:
    """Enable a plugin."""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=True))


@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str) -> dict:
    """Disable a plugin."""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=False))
