"""Tests for CapabilityScheduler."""

import pytest
from apps.core.abilities.base import AbilityContext, AbilityResult
from apps.core.abilities.scheduler import CapabilityScheduler
from apps.core.config.schemas import (
    CapabilitiesConfig,
    CapabilityToggle,
    StarAbilityToggle,
    StarEntry,
    StarRegistry,
)


class DummyRegistry:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def get_tool_schemas(self) -> list[dict]:
        return [
            {"type": "function", "function": {"name": "alpha", "description": "", "parameters": {}}},
            {"type": "function", "function": {"name": "beta", "description": "", "parameters": {}}},
        ]

    async def execute(self, ability_name: str, params: dict, context: AbilityContext):
        self.executed.append(ability_name)
        return AbilityResult(success=True, data=ability_name)


class DummyOwnerProvider:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def get_ability_owner(self, ability_name: str) -> str | None:
        return self._mapping.get(ability_name)


@pytest.mark.asyncio
async def test_scheduler_filters_tools_and_blocks_execute():
    config = CapabilitiesConfig(
        default_enabled=True,
        allow_tools_by_default=True,
        capabilities={"alpha": CapabilityToggle(enabled=False)},
    )
    scheduler = CapabilityScheduler(registry=DummyRegistry(), config=config)

    tools = scheduler.get_tool_schemas()
    tool_names = [tool["function"]["name"] for tool in tools]
    assert tool_names == ["beta"]

    context = AbilityContext(user_id="u1", session_id="s1")
    result = await scheduler.execute("alpha", {}, context)
    assert result.success is False
    assert result.error and "disabled" in result.error


@pytest.mark.asyncio
async def test_scheduler_applies_star_toggles():
    config = CapabilitiesConfig(
        default_enabled=True,
        allow_tools_by_default=True,
    )
    star_registry = StarRegistry(
        stars=[
            StarEntry(
                name="plugin-a",
                enabled=True,
                allow_tools=True,
                abilities={
                    "beta": StarAbilityToggle(enabled=False, allow_tools=False),
                },
            )
        ]
    )
    owner_provider = DummyOwnerProvider({"beta": "plugin-a"})
    scheduler = CapabilityScheduler(
        registry=DummyRegistry(),
        config=config,
        star_registry=star_registry,
        owner_provider=owner_provider,
    )

    tools = scheduler.get_tool_schemas()
    tool_names = [tool["function"]["name"] for tool in tools]
    assert tool_names == ["alpha"]

    context = AbilityContext(user_id="u1", session_id="s1")
    result = await scheduler.execute("beta", {}, context)
    assert result.success is False
    assert result.error and "disabled" in result.error
