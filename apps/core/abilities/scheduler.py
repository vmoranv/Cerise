"""Capability scheduling for abilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..config.schemas import CapabilitiesConfig, StarRegistry
from .base import AbilityContext, AbilityResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CapabilityDecision:
    """Resolved capability decision for an ability."""

    enabled: bool
    allow_tools: bool
    priority: int


class AbilityOwnerProvider(Protocol):
    """Provide the owning module for an ability."""

    def get_ability_owner(self, ability_name: str) -> str | None:
        """Return the owner name for an ability, if any."""


class CapabilityScheduler:
    """Ability scheduler driven by configuration."""

    def __init__(
        self,
        *,
        registry,
        config: CapabilitiesConfig | None = None,
        star_registry: StarRegistry | None = None,
        owner_provider: AbilityOwnerProvider | None = None,
    ) -> None:
        self._registry = registry
        self._config = config or CapabilitiesConfig()
        self._star_registry = star_registry
        self._owner_provider = owner_provider

    def _resolve(self, ability_name: str) -> CapabilityDecision:
        override = self._config.capabilities.get(ability_name)
        if override is not None:
            base = CapabilityDecision(
                enabled=override.enabled,
                allow_tools=override.allow_tools,
                priority=override.priority,
            )
        else:
            base = CapabilityDecision(
                enabled=self._config.default_enabled,
                allow_tools=self._config.allow_tools_by_default,
                priority=0,
            )

        star_decision = self._resolve_star(ability_name)
        if star_decision is None:
            return base

        return CapabilityDecision(
            enabled=base.enabled and star_decision.enabled,
            allow_tools=base.allow_tools and star_decision.allow_tools,
            priority=base.priority,
        )

    def decision_for(self, ability_name: str) -> CapabilityDecision:
        """Return the resolved capability decision for an ability."""

        return self._resolve(ability_name)

    def _resolve_star(self, ability_name: str) -> CapabilityDecision | None:
        if not self._star_registry or not self._owner_provider:
            return None
        owner = self._owner_provider.get_ability_owner(ability_name)
        if not owner:
            return None
        entry = self._star_registry.get_star(owner)
        if not entry:
            return None
        ability_toggle = entry.get_ability(ability_name)
        enabled = entry.enabled
        allow_tools = entry.allow_tools
        if ability_toggle:
            enabled = enabled and ability_toggle.enabled
            allow_tools = allow_tools and ability_toggle.allow_tools
        return CapabilityDecision(enabled=enabled, allow_tools=allow_tools, priority=0)

    def get_tool_schemas(self) -> list[dict]:
        """Return tool schemas filtered by capability config."""
        schemas = self._registry.get_tool_schemas()
        filtered: list[tuple[int, dict]] = []

        for schema in schemas:
            name = schema.get("function", {}).get("name", "")
            if not name:
                continue
            decision = self._resolve(name)
            if not (decision.enabled and decision.allow_tools):
                continue
            filtered.append((decision.priority, schema))

        filtered.sort(key=lambda item: item[0], reverse=True)
        return [schema for _, schema in filtered]

    async def execute(self, ability_name: str, params: dict, context: AbilityContext):
        """Execute an ability if enabled by config."""
        decision = self._resolve(ability_name)
        if not decision.enabled:
            logger.info("Ability '%s' disabled by capability config", ability_name)
            return AbilityResult(success=False, error=f"Ability '{ability_name}' disabled")

        if not decision.allow_tools:
            logger.info("Ability '%s' tool execution disabled by capability config", ability_name)
            return AbilityResult(success=False, error=f"Ability '{ability_name}' tool execution disabled")

        return await self._registry.execute(ability_name, params, context)
