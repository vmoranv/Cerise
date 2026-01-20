"""Admin provider routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...config import ProviderConfig, get_config_loader
from .models import ProviderCreateRequest

router = APIRouter()


@router.get("/providers")
async def list_providers(include: str | None = None) -> dict:
    """List all configured providers."""
    loader = get_config_loader()
    config = loader.get_providers_config()
    providers = [p.model_dump() for p in config.providers]

    include_set = {item.strip().lower() for item in include.split(",") if item.strip()} if include else set()
    if include_set & {"models", "capabilities"}:
        from ...ai.providers import ProviderRegistry

        if not ProviderRegistry._initialized:
            ProviderRegistry.load_from_config()

        for provider in providers:
            provider_id = provider.get("id", "")
            instance = ProviderRegistry.get(provider_id) if provider_id else None
            info = ProviderRegistry.get_provider_info(provider_id) if instance else None
            if "models" in include_set:
                provider["models"] = info["models"] if info else []
            if "capabilities" in include_set:
                provider["capabilities"] = info["capabilities"] if info else None

    return {
        "default": config.default,
        "providers": providers,
    }


@router.get("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str) -> dict:
    """List available models for a provider."""
    from ...ai.providers import ProviderRegistry

    provider = ProviderRegistry.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return {
        "provider_id": provider_id,
        "models": provider.available_models,
    }


@router.post("/providers")
async def add_provider(request: ProviderCreateRequest) -> dict:
    """Add a new provider."""
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
    """Update a provider."""
    loader = get_config_loader()
    config = loader.get_providers_config()

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
    """Delete a provider."""
    loader = get_config_loader()

    if loader.remove_provider(provider_id):
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Provider not found")


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str) -> dict:
    """Test provider connection."""
    from ...ai.providers import ProviderRegistry

    loader = get_config_loader()
    config = loader.get_providers_config()

    provider_exists = any(p.id == provider_id for p in config.providers)
    if not provider_exists:
        raise HTTPException(status_code=404, detail="Provider not found")

    result = await ProviderRegistry.test_connection(provider_id)
    return result


@router.post("/providers/{provider_id}/set-default")
async def set_default_provider(provider_id: str) -> dict:
    """Set default provider."""
    loader = get_config_loader()
    config = loader.get_providers_config()

    for p in config.providers:
        if p.id == provider_id:
            config.default = provider_id
            loader.save_providers_config(config)
            return {"status": "updated", "default": provider_id}

    raise HTTPException(status_code=404, detail="Provider not found")
