"""
Plugin lifecycle helpers.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from .name_safety import validate_plugin_name
from .plugin_types import LoadedPlugin, PluginManifest, normalize_abilities
from .protocol import JsonRpcRequest, Methods
from .transport import BaseTransport, HttpTransport, StdioTransport

logger = logging.getLogger(__name__)


def _extract_abilities(init_result: dict, *, manifest: PluginManifest) -> list[dict]:
    """Extract abilities from plugin initialize() response, with fallbacks."""

    if not isinstance(init_result, dict):
        return normalize_abilities(manifest.abilities)

    for key in ("abilities", "skills", "tools"):
        abilities = init_result.get(key)
        if abilities:
            return normalize_abilities(abilities)

    mcp_block = init_result.get("mcp")
    if isinstance(mcp_block, dict):
        mcp_tools = mcp_block.get("tools")
        if mcp_tools:
            return normalize_abilities(mcp_tools)

    return normalize_abilities(manifest.abilities)


class LifecycleMixin:
    plugins_dir: Path
    _plugins: dict[str, LoadedPlugin]
    _ability_map: dict[str, str]

    async def load(self, plugin_name: str, config: dict | None = None) -> bool:
        """Load and start a plugin."""
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            logger.warning("Invalid plugin name: %r", plugin_name)
            return False

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

        abilities = _extract_abilities(response.result, manifest=manifest)

        plugin = LoadedPlugin(
            manifest=manifest,
            transport=transport,
            plugin_dir=plugin_dir,
            config=config or {},
            abilities=abilities,
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
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            logger.warning("Invalid plugin name: %r", plugin_name)
            return False

        if plugin_name not in self._plugins:
            return False

        plugin = self._plugins[plugin_name]

        try:
            shutdown_request = JsonRpcRequest(method=Methods.SHUTDOWN)
            await asyncio.wait_for(
                plugin.transport.send(shutdown_request),
                timeout=5.0,
            )
        except Exception as exc:
            logger.debug("Plugin shutdown failed for %s: %s", plugin_name, exc)

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
        try:
            plugin_name = validate_plugin_name(plugin_name)
        except ValueError:
            logger.warning("Invalid plugin name: %r", plugin_name)
            return False

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
        transport = (manifest.transport or "").lower()
        if transport == "http":
            if not manifest.http_url:
                logger.error("HTTP transport requires http_url: %s", manifest.name)
                return None
            return HttpTransport(manifest.http_url)

        language = (manifest.language or "").lower()
        command = manifest.command
        if not command:
            if language == "python":
                python_exec = "python"
                try:
                    from ..config import get_config_loader

                    venv_dir_name = get_config_loader().get_app_config().plugins.python_venv_dir or ".venv"
                except Exception:
                    venv_dir_name = ".venv"

                venv_dir = plugin_dir / venv_dir_name
                python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                if python_path.exists():
                    python_exec = str(python_path)

                command = f'"{python_exec}" "{manifest.entry}"'
            elif language in ("node", "nodejs", "javascript"):
                command = f'node "{manifest.entry}"'
            elif language in ("go", "golang"):
                command = f'go run "{manifest.entry}"'
            elif language in ("binary", "exe", "native", "cpp", "c++", "cxx", "c", "rust"):
                command = manifest.entry
            else:
                logger.error("Unknown language: %s", manifest.language)
                return None

        return StdioTransport(
            command=command,
            cwd=str(plugin_dir),
        )
