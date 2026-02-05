"""
Plugin registry helpers.
"""

import shutil
from pathlib import Path

from ..config import InstalledPlugin
from .name_safety import validate_plugin_name


class RegistryMixin:
    loader: object
    plugins_dir: Path

    async def uninstall(self, plugin_name: str) -> bool:
        """Uninstall a plugin."""
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            return False

        plugin_dir = self.plugins_dir / plugin_name

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        return self.loader.unregister_plugin(plugin_name)

    def list_installed(self) -> list[InstalledPlugin]:
        """List installed plugins."""
        registry = self.loader.get_plugins_registry()
        return registry.plugins

    def get_plugin_info(self, plugin_name: str) -> InstalledPlugin | None:
        """Get plugin info."""
        registry = self.loader.get_plugins_registry()
        for plugin in registry.plugins:
            if plugin.name == plugin_name:
                return plugin
        return None
