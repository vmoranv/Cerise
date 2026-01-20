"""
Plugin Loader

Discovers and loads plugins from the plugins directory.
"""

import importlib.util
import json
import logging
from pathlib import Path

from .base import BaseAbility
from .loader_types import LoadedPlugin
from .loader_utils import merge_config, validate_manifest
from .registry import AbilityRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """Manages plugin discovery, loading, and lifecycle"""

    def __init__(self, plugins_dir: str | Path):
        self.plugins_dir = Path(plugins_dir)
        self._loaded_plugins: dict[str, LoadedPlugin] = {}

    async def discover(self) -> list[str]:
        """Discover available plugins"""
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return []

        plugins = []
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue
            if (plugin_dir / "manifest.json").exists():
                plugins.append(plugin_dir.name)
                logger.debug(f"Discovered plugin: {plugin_dir.name}")

        return plugins

    async def load(self, plugin_name: str, config: dict | None = None) -> bool:
        """Load a specific plugin"""
        plugin_dir = self.plugins_dir / plugin_name
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            logger.error(f"Plugin manifest not found: {manifest_path}")
            return False

        try:
            # Load manifest
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            # Validate manifest
            if not validate_manifest(manifest):
                return False

            # Load plugin module
            entry_point = plugin_dir / manifest["entry_point"]
            class_name = manifest["class_name"]

            spec = importlib.util.spec_from_file_location(manifest["name"], entry_point)
            if not spec or not spec.loader:
                logger.error(f"Failed to create module spec for {plugin_name}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get ability class
            ability_class: type[BaseAbility] = getattr(module, class_name)

            # Merge config from manifest defaults
            plugin_config = merge_config(manifest.get("config_schema", {}), config)

            # Instantiate
            ability_instance = ability_class(config=plugin_config)

            # Call on_load
            await ability_instance.on_load()

            # Register
            AbilityRegistry.register(ability_instance)

            # Track loaded plugin
            self._loaded_plugins[plugin_name] = LoadedPlugin(
                name=plugin_name,
                manifest=manifest,
                module=module,
                instance=ability_instance,
            )

            logger.info(f"Loaded plugin: {plugin_name} v{manifest.get('version', '?')}")
            return True

        except Exception as e:
            logger.exception(f"Failed to load plugin {plugin_name}: {e}")
            return False

    async def unload(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name not in self._loaded_plugins:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return False

        loaded = self._loaded_plugins[plugin_name]

        try:
            # Call on_unload
            await loaded.instance.on_unload()

            # Unregister
            AbilityRegistry.unregister(loaded.instance.name)

            # Remove from tracking
            del self._loaded_plugins[plugin_name]

            logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.exception(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    async def reload(self, plugin_name: str) -> bool:
        """Hot reload a plugin"""
        config = None
        if plugin_name in self._loaded_plugins:
            # Preserve config
            config = self._loaded_plugins[plugin_name].manifest.get("_runtime_config")
            await self.unload(plugin_name)

        return await self.load(plugin_name, config)

    async def load_all(self, config_map: dict[str, dict] | None = None) -> dict[str, bool]:
        """Load all discovered plugins"""
        config_map = config_map or {}
        results = {}

        plugins = await self.discover()
        for plugin_name in plugins:
            config = config_map.get(plugin_name)
            results[plugin_name] = await self.load(plugin_name, config)

        return results

    async def unload_all(self) -> None:
        """Unload all loaded plugins"""
        for plugin_name in list(self._loaded_plugins.keys()):
            await self.unload(plugin_name)

    def get_loaded_plugins(self) -> list[str]:
        """Get list of loaded plugin names"""
        return list(self._loaded_plugins.keys())

    def get_plugin_info(self, plugin_name: str) -> dict | None:
        """Get plugin manifest info"""
        if plugin_name in self._loaded_plugins:
            return self._loaded_plugins[plugin_name].manifest
        return None

