"""Admin ability routes (introspection + safe execution)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

from ...abilities import AbilityContext, AbilityRegistry, CapabilityScheduler
from ...config import get_config_loader
from ..dependencies import get_services
from .models import AbilityExecuteRequest

if TYPE_CHECKING:
    from ..container import AppServices

router = APIRouter()


def _build_scheduler(services: AppServices) -> CapabilityScheduler:
    loader = get_config_loader()
    app_config = loader.get_app_config()
    star_registry = loader.get_star_registry()
    return CapabilityScheduler(
        registry=AbilityRegistry,
        config=app_config.capabilities,
        star_registry=star_registry,
        owner_provider=services.plugin_manager,
    )


@router.get("/abilities")
async def list_abilities(services: AppServices = Depends(get_services)) -> dict[str, Any]:
    scheduler = _build_scheduler(services)

    items: list[dict[str, Any]] = []
    for name, ability in AbilityRegistry.get_all().items():
        decision = scheduler.decision_for(name)
        owner = services.plugin_manager.get_ability_owner(name)
        items.append(
            {
                "name": name,
                "display_name": getattr(ability, "display_name", name),
                "description": getattr(ability, "description", ""),
                "ability_type": getattr(getattr(ability, "ability_type", None), "value", ""),
                "category": getattr(getattr(ability, "category", None), "value", ""),
                "required_permissions": list(getattr(ability, "required_permissions", [])),
                "enabled": decision.enabled,
                "allow_tools": decision.allow_tools,
                "priority": decision.priority,
                "owner": owner,
            },
        )

    items.sort(key=lambda entry: entry.get("name", ""))
    return {"abilities": items}


@router.get("/abilities/{name}")
async def get_ability(name: str, services: AppServices = Depends(get_services)) -> dict[str, Any]:
    ability = AbilityRegistry.get(name)
    if not ability:
        raise HTTPException(status_code=404, detail="Ability not found")

    scheduler = _build_scheduler(services)
    decision = scheduler.decision_for(name)
    owner = services.plugin_manager.get_ability_owner(name)

    return {
        "name": name,
        "display_name": getattr(ability, "display_name", name),
        "description": getattr(ability, "description", ""),
        "ability_type": getattr(getattr(ability, "ability_type", None), "value", ""),
        "category": getattr(getattr(ability, "category", None), "value", ""),
        "required_permissions": list(getattr(ability, "required_permissions", [])),
        "parameters_schema": getattr(ability, "parameters_schema", {}),
        "tool_schema": getattr(ability, "to_tool_schema", lambda: {})(),
        "enabled": decision.enabled,
        "allow_tools": decision.allow_tools,
        "priority": decision.priority,
        "owner": owner,
    }


@router.get("/abilities/tool-schemas")
async def list_tool_schemas(services: AppServices = Depends(get_services)) -> dict[str, Any]:
    scheduler = _build_scheduler(services)
    return {"tools": scheduler.get_tool_schemas()}


@router.post("/abilities/{name}/execute")
async def execute_ability(
    name: str,
    request: AbilityExecuteRequest,
    services: AppServices = Depends(get_services),
) -> dict[str, Any]:
    scheduler = _build_scheduler(services)

    loader = get_config_loader()
    config = loader.get_app_config()
    context = AbilityContext(
        user_id=request.user_id or "admin",
        session_id=request.session_id or "admin",
        permissions=list(config.tools.permissions),
    )

    result = await scheduler.execute(name, request.params or {}, context)
    return {
        "result": {
            "success": bool(getattr(result, "success", False)),
            "data": getattr(result, "data", None),
            "error": getattr(result, "error", None),
            "emotion_hint": getattr(result, "emotion_hint", None),
        },
    }
