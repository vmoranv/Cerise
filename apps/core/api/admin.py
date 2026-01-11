"""
Admin API

REST API for managing configuration, plugins, and providers.
"""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import (
    AppConfig,
    CharacterConfig,
    ProviderConfig,
    get_config_loader,
)
from ..plugins.installer import PluginInstaller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ----- Request/Response Models -----


class GitHubInstallRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class ProviderCreateRequest(BaseModel):
    id: str
    type: str
    name: str = ""
    enabled: bool = True
    config: dict = {}


class ConfigUpdateRequest(BaseModel):
    config: dict


class PluginConfigUpdate(BaseModel):
    enabled: bool | None = None
    config: dict | None = None


# ----- Config Endpoints -----


@router.get("/config")
async def get_config() -> dict:
    """Get current application configuration"""
    loader = get_config_loader()
    config = loader.get_app_config()
    return config.model_dump()


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> dict:
    """Update application configuration"""
    loader = get_config_loader()

    try:
        # Merge with existing config
        current = loader.get_app_config().model_dump()
        current.update(request.config)
        new_config = AppConfig(**current)
        loader.save_app_config(new_config)
        return {"status": "updated", "config": new_config.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ----- Provider Endpoints -----


@router.get("/providers")
async def list_providers() -> dict:
    """List all configured providers"""
    loader = get_config_loader()
    config = loader.get_providers_config()
    return {
        "default": config.default,
        "providers": [p.model_dump() for p in config.providers],
    }


@router.post("/providers")
async def add_provider(request: ProviderCreateRequest) -> dict:
    """Add a new provider"""
    loader = get_config_loader()

    provider = ProviderConfig(
        id=request.id,
        type=request.type,
        name=request.name or request.id,
        enabled=request.enabled,
        config=request.config,
    )

    loader.add_provider(provider)
    return {"status": "added", "provider": provider.model_dump()}


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, request: ProviderCreateRequest) -> dict:
    """Update a provider"""
    loader = get_config_loader()
    config = loader.get_providers_config()

    # Find and update
    for i, p in enumerate(config.providers):
        if p.id == provider_id:
            config.providers[i] = ProviderConfig(
                id=provider_id,
                type=request.type,
                name=request.name,
                enabled=request.enabled,
                config=request.config,
            )
            loader.save_providers_config(config)
            return {"status": "updated"}

    raise HTTPException(status_code=404, detail="Provider not found")


@router.delete("/providers/{provider_id}")
async def delete_provider(provider_id: str) -> dict:
    """Delete a provider"""
    loader = get_config_loader()

    if loader.remove_provider(provider_id):
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str) -> dict:
    """Test provider connection"""
    from ..ai.providers import ProviderRegistry

    # Ensure provider exists in config
    loader = get_config_loader()
    config = loader.get_providers_config()

    provider_exists = any(p.id == provider_id for p in config.providers)
    if not provider_exists:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Run connection test
    result = await ProviderRegistry.test_connection(provider_id)
    return result


@router.post("/providers/{provider_id}/set-default")
async def set_default_provider(provider_id: str) -> dict:
    """Set default provider"""
    loader = get_config_loader()
    config = loader.get_providers_config()

    # Verify provider exists
    for p in config.providers:
        if p.id == provider_id:
            config.default = provider_id
            loader.save_providers_config(config)
            return {"status": "updated", "default": provider_id}

    raise HTTPException(status_code=404, detail="Provider not found")


# ----- Character Endpoints -----


@router.get("/characters")
async def list_characters() -> dict:
    """List available characters"""
    loader = get_config_loader()
    return {"characters": loader.list_characters()}


@router.get("/characters/{name}")
async def get_character(name: str) -> dict:
    """Get character configuration"""
    loader = get_config_loader()
    try:
        config = loader.load_character_config(name)
        return config.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Character not found") from e


@router.put("/characters/{name}")
async def update_character(name: str, config: dict) -> dict:
    """Update character configuration"""
    loader = get_config_loader()
    try:
        char_config = CharacterConfig(**config)
        loader.save_character_config(char_config, name)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ----- Plugin Endpoints -----


@router.get("/plugins")
async def list_plugins() -> dict:
    """List installed plugins"""
    installer = PluginInstaller()
    plugins = installer.list_installed()
    return {"plugins": [p.model_dump() for p in plugins]}


@router.post("/plugins/install/github")
async def install_from_github(request: GitHubInstallRequest) -> dict:
    """Install plugin from GitHub"""
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
    """Install plugin from uploaded zip file"""
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
    """Uninstall a plugin"""
    installer = PluginInstaller()

    if await installer.uninstall(name):
        return {"status": "uninstalled"}

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/plugins/{name}")
async def get_plugin(name: str) -> dict:
    """Get plugin info"""
    installer = PluginInstaller()
    plugin = installer.get_plugin_info(name)

    if plugin:
        return plugin.model_dump()

    raise HTTPException(status_code=404, detail="Plugin not found")


@router.put("/plugins/{name}")
async def update_plugin_config(name: str, request: PluginConfigUpdate) -> dict:
    """Update plugin configuration (enable/disable, config)"""
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
    """Enable a plugin"""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=True))


@router.post("/plugins/{name}/disable")
async def disable_plugin(name: str) -> dict:
    """Disable a plugin"""
    return await update_plugin_config(name, PluginConfigUpdate(enabled=False))
