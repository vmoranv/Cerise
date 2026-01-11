"""
Plugin Manager

Manages plugin lifecycle: discovery, loading, and communication.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .protocol import (
    ExecuteResult,
    JsonRpcRequest,
    Methods,
)
from .transport import BaseTransport, HttpTransport, StdioTransport

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Plugin manifest data"""

    name: str
    version: str
    display_name: str = ""
    description: str = ""
    author: str = ""

    # Runtime configuration
    language: str = "python"
    entry: str = "main.py"
    command: str = ""
    transport: str = "stdio"  # "stdio" or "http"
    http_url: str = ""

    # Abilities
    abilities: list[dict] = field(default_factory=list)

    # Permissions and config
    permissions: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        runtime = data.get("runtime", {})
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            display_name=data.get("display_name", data.get("name", "")),
            description=data.get("description", ""),
            author=data.get("author", ""),
            language=runtime.get("language", "python"),
            entry=runtime.get("entry", "main.py"),
            command=runtime.get("command", ""),
            transport=runtime.get("transport", "stdio"),
            http_url=runtime.get("http_url", ""),
            abilities=data.get("abilities", []),
            permissions=data.get("permissions", []),
            config_schema=data.get("config_schema", {}),
        )


@dataclass
class LoadedPlugin:
    """Represents a loaded plugin"""

    manifest: PluginManifest
    transport: BaseTransport
    plugin_dir: Path
    config: dict = field(default_factory=dict)
    abilities: list[dict] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def is_running(self) -> bool:
        return self.transport.is_connected


class PluginManager:
    """Manages all plugins"""

    def __init__(self, plugins_dir: str | Path):
        self.plugins_dir = Path(plugins_dir)
        self._plugins: dict[str, LoadedPlugin] = {}
        self._ability_map: dict[str, str] = {}  # ability_name -> plugin_name

    async def discover(self) -> list[PluginManifest]:
        """Discover available plugins"""
        manifests = []

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return manifests

        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            manifest_path = plugin_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        data = json.load(f)
                    manifest = PluginManifest.from_dict(data)
                    manifests.append(manifest)
                    logger.debug(f"Discovered plugin: {manifest.name}")
                except Exception as e:
                    logger.warning(f"Failed to read manifest {manifest_path}: {e}")

        return manifests

    async def load(
        self,
        plugin_name: str,
        config: dict | None = None,
    ) -> bool:
        """Load and start a plugin"""
        plugin_dir = self.plugins_dir / plugin_name
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
            manifest = PluginManifest.from_dict(data)
        except Exception as e:
            logger.exception(f"Failed to read manifest: {e}")
            return False

        # Create transport
        transport = self._create_transport(manifest, plugin_dir)
        if not transport:
            return False

        # Connect
        if not await transport.connect():
            return False

        # Initialize plugin
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
            logger.error(f"Plugin init failed: {response.error.message}")
            await transport.disconnect()
            return False

        # Register plugin
        plugin = LoadedPlugin(
            manifest=manifest,
            transport=transport,
            plugin_dir=plugin_dir,
            config=config or {},
            abilities=response.result.get("abilities", manifest.abilities),
        )

        self._plugins[plugin_name] = plugin

        # Register abilities
        for ability in plugin.abilities:
            ability_name = ability.get("name", "")
            if ability_name:
                self._ability_map[ability_name] = plugin_name

        logger.info(f"Loaded plugin: {plugin_name} v{manifest.version}")
        return True

    async def unload(self, plugin_name: str) -> bool:
        """Stop and unload a plugin"""
        if plugin_name not in self._plugins:
            return False

        plugin = self._plugins[plugin_name]

        # Send shutdown
        try:
            shutdown_request = JsonRpcRequest(method=Methods.SHUTDOWN)
            await asyncio.wait_for(
                plugin.transport.send(shutdown_request),
                timeout=5.0,
            )
        except Exception:
            pass

        # Disconnect
        await plugin.transport.disconnect()

        # Unregister abilities
        for ability in plugin.abilities:
            ability_name = ability.get("name", "")
            if ability_name in self._ability_map:
                del self._ability_map[ability_name]

        del self._plugins[plugin_name]
        logger.info(f"Unloaded plugin: {plugin_name}")
        return True

    async def reload(self, plugin_name: str) -> bool:
        """Reload a plugin"""
        config = None
        if plugin_name in self._plugins:
            config = self._plugins[plugin_name].config
            await self.unload(plugin_name)

        return await self.load(plugin_name, config)

    async def load_all(self, config_map: dict[str, dict] | None = None) -> dict[str, bool]:
        """Load all discovered plugins"""
        config_map = config_map or {}
        results = {}

        manifests = await self.discover()
        for manifest in manifests:
            config = config_map.get(manifest.name)
            results[manifest.name] = await self.load(manifest.name, config)

        return results

    async def unload_all(self) -> None:
        """Unload all plugins"""
        for plugin_name in list(self._plugins):
            await self.unload(plugin_name)

    async def execute(
        self,
        ability_name: str,
        params: dict,
        context: dict,
    ) -> ExecuteResult:
        """Execute an ability"""
        # Find plugin
        plugin_name = self._ability_map.get(ability_name)
        if not plugin_name or plugin_name not in self._plugins:
            return ExecuteResult(
                success=False,
                error=f"Ability not found: {ability_name}",
            )

        plugin = self._plugins[plugin_name]

        if not plugin.is_running:
            return ExecuteResult(
                success=False,
                error=f"Plugin not running: {plugin_name}",
            )

        # Execute
        request = JsonRpcRequest(
            method=Methods.EXECUTE,
            params={
                "ability": ability_name,
                "params": params,
                "context": context,
            },
        )

        response = await plugin.transport.send(request)

        if response.error:
            return ExecuteResult(
                success=False,
                error=response.error.message,
            )

        result = response.result or {}
        return ExecuteResult(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            emotion_hint=result.get("emotion_hint"),
        )

    async def health_check(self, plugin_name: str) -> bool:
        """Check plugin health"""
        if plugin_name not in self._plugins:
            return False

        plugin = self._plugins[plugin_name]
        if not plugin.is_running:
            return False

        request = JsonRpcRequest(method=Methods.HEALTH)
        response = await plugin.transport.send(request)

        if response.error:
            return False

        return response.result.get("healthy", False)

    def get_plugin(self, plugin_name: str) -> LoadedPlugin | None:
        """Get loaded plugin"""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> list[str]:
        """List loaded plugins"""
        return list(self._plugins.keys())

    def list_abilities(self) -> list[dict]:
        """List all abilities from all plugins"""
        abilities = []
        for plugin in self._plugins.values():
            for ability in plugin.abilities:
                abilities.append(
                    {
                        **ability,
                        "plugin": plugin.name,
                    }
                )
        return abilities

    def get_ability_schema(self, ability_name: str) -> dict | None:
        """Get ability schema for LLM tool calling"""
        plugin_name = self._ability_map.get(ability_name)
        if not plugin_name or plugin_name not in self._plugins:
            return None

        plugin = self._plugins[plugin_name]
        for ability in plugin.abilities:
            if ability.get("name") == ability_name:
                return {
                    "type": "function",
                    "function": {
                        "name": ability_name,
                        "description": ability.get("description", ""),
                        "parameters": ability.get("parameters", {}),
                    },
                }
        return None

    def get_all_tool_schemas(self) -> list[dict]:
        """Get all ability schemas for LLM"""
        schemas = []
        for ability_name in self._ability_map:
            schema = self.get_ability_schema(ability_name)
            if schema:
                schemas.append(schema)
        return schemas

    def _create_transport(
        self,
        manifest: PluginManifest,
        plugin_dir: Path,
    ) -> BaseTransport | None:
        """Create transport based on manifest"""
        if manifest.transport == "http":
            if not manifest.http_url:
                logger.error(f"HTTP transport requires http_url: {manifest.name}")
                return None
            return HttpTransport(manifest.http_url)

        # Default: stdio
        command = manifest.command
        if not command:
            # Auto-generate command based on language
            if manifest.language == "python":
                command = f"python {manifest.entry}"
            elif manifest.language in ("node", "nodejs", "javascript"):
                command = f"node {manifest.entry}"
            else:
                logger.error(f"Unknown language: {manifest.language}")
                return None

        return StdioTransport(
            command=command,
            cwd=str(plugin_dir),
        )
