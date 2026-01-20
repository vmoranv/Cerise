"""
Plugin lifecycle helpers.
"""

import asyncio
import json
import logging
from pathlib import Path

from .plugin_types import LoadedPlugin, PluginManifest
from .protocol import JsonRpcRequest, Methods
from .transport import BaseTransport, HttpTransport, StdioTransport

logger = logging.getLogger(__name__)


class LifecycleMixin:
    plugins_dir: Path
    _plugins: dict[str, LoadedPlugin]
    _ability_map: dict[str, str]

    async def load(self, plugin_name: str, config: dict | None = None) -> bool:
        """Load and start a plugin."""
        plugin_dir = self.plugins_dir / plugin_name
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            logger.error("Plugin not found: %s", plugin_name)
            return False

        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            manifest = PluginManifest.from_dict(data)
        except Exception as exc:
            logger.exception("Failed to read manifest: %s", exc)
            return False

        transport = self._create_transport(manifest, plugin_dir)
        if not transport:
            return False

        if not await transport.connect():
            return False

        init_request = JsonRpcRequest(
            method=Methods.INITIALIZE,
            params={
                "plugin_name": manifest.name,
                "config": config or {},
                "permissions": manifest.permissions,
            },
        )

        response = await transport.send(init_request)
        if response.error:
            logger.error("Plugin init failed: %s", response.error.message)
            await transport.disconnect()
            return False

        plugin = LoadedPlugin(
            manifest=manifest,
            transport=transport,
            plugin_dir=plugin_dir,
            config=config or {},
            abilities=response.result.get("abilities", manifest.abilities),
        )

        self._plugins[plugin_name] = plugin

        for ability in plugin.abilities:
            ability_name = ability.get("name", "")
            if ability_name:
                self._ability_map[ability_name] = plugin_name

        logger.info("Loaded plugin: %s v%s", plugin_name, manifest.version)
        return True

    async def unload(self, plugin_name: str) -> bool:
        """Stop and unload a plugin."""
        if plugin_name not in self._plugins:
            return False

        plugin = self._plugins[plugin_name]

        try:
            shutdown_request = JsonRpcRequest(method=Methods.SHUTDOWN)
            await asyncio.wait_for(
                plugin.transport.send(shutdown_request),
                timeout=5.0,
            )
        except Exception:
            pass

        await plugin.transport.disconnect()

        for ability in plugin.abilities:
            ability_name = ability.get("name", "")
            if ability_name in self._ability_map:
                del self._ability_map[ability_name]

        del self._plugins[plugin_name]
        logger.info("Unloaded plugin: %s", plugin_name)
        return True

    async def reload(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        config = None
        if plugin_name in self._plugins:
            config = self._plugins[plugin_name].config
            await self.unload(plugin_name)

        return await self.load(plugin_name, config)

    async def load_all(self, config_map: dict[str, dict] | None = None) -> dict[str, bool]:
        """Load all discovered plugins."""
        config_map = config_map or {}
        results = {}

        manifests = await self.discover()
        for manifest in manifests:
            config = config_map.get(manifest.name)
            results[manifest.name] = await self.load(manifest.name, config)

        return results

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for plugin_name in list(self._plugins):
            await self.unload(plugin_name)

    def _create_transport(self, manifest: PluginManifest, plugin_dir: Path) -> BaseTransport | None:
        """Create transport based on manifest."""
        if manifest.transport == "http":
            if not manifest.http_url:
                logger.error("HTTP transport requires http_url: %s", manifest.name)
                return None
            return HttpTransport(manifest.http_url)

        command = manifest.command
        if not command:
            if manifest.language == "python":
                command = f"python {manifest.entry}"
            elif manifest.language in ("node", "nodejs", "javascript"):
                command = f"node {manifest.entry}"
            else:
                logger.error("Unknown language: %s", manifest.language)
                return None

        return StdioTransport(
            command=command,
            cwd=str(plugin_dir),
        )
