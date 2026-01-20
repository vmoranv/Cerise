"""
Provider Registry

Central registry for managing AI providers with configuration-driven loading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseProvider
from .registry_access import ProviderRegistryAccessMixin
from .registry_config import ProviderRegistryConfigMixin

if TYPE_CHECKING:
    from ...config import ProviderConfig


class ProviderRegistry(ProviderRegistryConfigMixin, ProviderRegistryAccessMixin):
    """Registry for AI provider management with config-driven loading."""

    _provider_types: dict[str, type[BaseProvider]] = {}
    _instances: dict[str, BaseProvider] = {}
    _configs: dict[str, ProviderConfig] = {}
    _default_provider: str | None = None
    _initialized: bool = False
