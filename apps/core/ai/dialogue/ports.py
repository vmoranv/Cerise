"""Dialogue engine protocol types."""

from __future__ import annotations

from typing import Protocol

from ...abilities import AbilityContext
from ..providers import BaseProvider


class ProviderRegistryProtocol(Protocol):
    """Minimal provider registry interface."""

    def get(self, provider_id: str) -> BaseProvider | None:
        """Get a provider instance by id."""


class AbilityRegistryProtocol(Protocol):
    """Minimal ability registry interface."""

    def get_tool_schemas(self) -> list[dict]:
        """Return tool schemas for the provider."""

    async def execute(self, ability_name: str, params: dict, context: AbilityContext):
        """Execute an ability by name."""
