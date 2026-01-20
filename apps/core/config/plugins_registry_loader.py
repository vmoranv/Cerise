"""
Plugins registry loading helpers.
"""

import json
import logging
from pathlib import Path

from .schemas import InstalledPlugin, PluginsRegistry

logger = logging.getLogger(__name__)


class PluginsRegistryLoaderMixin:
    data_dir: Path
    _plugins_registry: PluginsRegistry | None

    def load_plugins_registry(self) -> PluginsRegistry:
        """Load plugins registry."""
        registry_path = self.data_dir / "plugins.json"

        if not registry_path.exists():
            self._plugins_registry = PluginsRegistry()
            return self._plugins_registry

        try:
            with open(registry_path, encoding="utf-8") as f:
                data = json.load(f)
            self._plugins_registry = PluginsRegistry(**data)
        except Exception as exc:
            logger.warning("Failed to load plugins registry: %s", exc)
            self._plugins_registry = PluginsRegistry()

        return self._plugins_registry

    def save_plugins_registry(self, registry: PluginsRegistry) -> None:
        """Save plugins registry."""
        registry_path = self.data_dir / "plugins.json"

        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry.model_dump(), f, indent=2)

        self._plugins_registry = registry

    def get_plugins_registry(self) -> PluginsRegistry:
        """Get cached or load plugins registry."""
        if self._plugins_registry is None:
            self.load_plugins_registry()
        return self._plugins_registry  # type: ignore[return-value]

    def register_plugin(self, plugin: InstalledPlugin) -> None:
        """Register an installed plugin."""
        registry = self.get_plugins_registry()

        for i, existing in enumerate(registry.plugins):
            if existing.name == plugin.name:
                registry.plugins[i] = plugin
                self.save_plugins_registry(registry)
                return

        registry.plugins.append(plugin)
        self.save_plugins_registry(registry)

    def unregister_plugin(self, name: str) -> bool:
        """Unregister a plugin."""
        registry = self.get_plugins_registry()

        for i, plugin in enumerate(registry.plugins):
            if plugin.name == name:
                registry.plugins.pop(i)
                self.save_plugins_registry(registry)
                return True

        return False
