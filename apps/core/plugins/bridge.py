"""
Plugin Bridge

Bridges the Ability system with the Plugin system.
Allows AbilityRegistry to use plugins transparently.
"""

import logging

from ..abilities import AbilityContext, AbilityRegistry, AbilityResult
from .manager import PluginManager

logger = logging.getLogger(__name__)


class PluginBridge:
    """Bridges plugins to the ability system"""

    def __init__(self, plugin_manager: PluginManager):
        self.manager = plugin_manager
        self._registered = False

    async def register_plugin_abilities(self) -> None:
        """Register all plugin abilities to AbilityRegistry"""
        abilities = self.manager.list_abilities()

        for ability_info in abilities:
            ability_name = ability_info.get("name")
            if not ability_name:
                continue

            # Create a proxy ability that calls the plugin
            proxy = self._create_proxy_ability(ability_info)
            AbilityRegistry.register(proxy)

        self._registered = True
        logger.info(f"Registered {len(abilities)} plugin abilities")

    def _create_proxy_ability(self, ability_info: dict) -> "PluginProxyAbility":
        """Create a proxy ability for a plugin ability"""
        return PluginProxyAbility(
            ability_name=ability_info.get("name", ""),
            display_name=ability_info.get("display_name", ""),
            description=ability_info.get("description", ""),
            parameters_schema=ability_info.get("parameters", {}),
            plugin_name=ability_info.get("plugin", ""),
            plugin_manager=self.manager,
        )

    async def execute(
        self,
        ability_name: str,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Execute a plugin ability"""
        result = await self.manager.execute(
            ability_name=ability_name,
            params=params,
            context={
                "user_id": context.user_id,
                "session_id": context.session_id,
                "permissions": context.permissions,
            },
        )

        return AbilityResult(
            success=result.success,
            data=result.data,
            error=result.error,
            emotion_hint=result.emotion_hint,
        )

    def get_tool_schemas(self) -> list[dict]:
        """Get OpenAI-compatible tool schemas"""
        return self.manager.get_all_tool_schemas()


class PluginProxyAbility:
    """Proxy ability that forwards calls to plugin"""

    def __init__(
        self,
        ability_name: str,
        display_name: str,
        description: str,
        parameters_schema: dict,
        plugin_name: str,
        plugin_manager: PluginManager,
    ):
        self._name = ability_name
        self._display_name = display_name or ability_name
        self._description = description
        self._parameters_schema = parameters_schema
        self._plugin_name = plugin_name
        self._manager = plugin_manager

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def ability_type(self):
        from ..abilities import AbilityType

        return AbilityType.PLUGIN

    @property
    def category(self):
        from ..abilities import AbilityCategory

        return AbilityCategory.UTILITY

    @property
    def parameters_schema(self) -> dict:
        return self._parameters_schema

    @property
    def required_permissions(self) -> list[str]:
        return []

    async def execute(
        self,
        params: dict,
        context: AbilityContext,
    ) -> AbilityResult:
        """Forward execution to plugin"""
        result = await self._manager.execute(
            ability_name=self._name,
            params=params,
            context={
                "user_id": context.user_id,
                "session_id": context.session_id,
                "permissions": context.permissions,
            },
        )

        return AbilityResult(
            success=result.success,
            data=result.data,
            error=result.error,
            emotion_hint=result.emotion_hint,
        )

    async def validate_params(self, params: dict) -> bool:
        return True

    async def on_load(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    def to_tool_schema(self) -> dict:
        """Convert to OpenAI tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": self._description,
                "parameters": self._parameters_schema,
            },
        }
