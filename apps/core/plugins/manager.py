"""
Plugin Manager

Manages plugin lifecycle: discovery, loading, and communication.
"""

from pathlib import Path

from .plugin_discovery import DiscoveryMixin
from .plugin_execution import ExecutionMixin
from .plugin_lifecycle import LifecycleMixin
from .plugin_queries import QueryMixin
from .plugin_types import LoadedPlugin


class PluginManager(DiscoveryMixin, LifecycleMixin, ExecutionMixin, QueryMixin):
    """Manages all plugins."""

    def __init__(self, plugins_dir: str | Path):
        self.plugins_dir = Path(plugins_dir)
        self._plugins: dict[str, LoadedPlugin] = {}
        self._ability_map: dict[str, str] = {}
