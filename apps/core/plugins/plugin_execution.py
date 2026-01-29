"""
Plugin execution helpers.
"""

from .plugin_types import LoadedPlugin
from .protocol import ExecuteResult, JsonRpcRequest, Methods


class ExecutionMixin:
    _plugins: dict[str, LoadedPlugin]
    _ability_map: dict[str, str]

    async def execute(self, ability_name: str, params: dict, context: dict) -> ExecuteResult:
        """Execute an ability."""
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

        request = JsonRpcRequest(
            method=Methods.EXECUTE,
            params={
                "ability": ability_name,
                "skill": ability_name,
                "tool": ability_name,
                "name": ability_name,
                "params": params,
                "arguments": params,
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
        """Check plugin health."""
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
