"""
Plugin query helpers.
"""

from .plugin_types import LoadedPlugin


class QueryMixin:
    _plugins: dict[str, LoadedPlugin]
    _ability_map: dict[str, str]

    def get_plugin(self, plugin_name: str) -> LoadedPlugin | None:
        """Get loaded plugin."""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> list[str]:
        """List loaded plugins."""
        return list(self._plugins.keys())

    def list_abilities(self) -> list[dict]:
        """List all abilities from all plugins."""
        abilities = []
        for plugin in self._plugins.values():
            for ability in plugin.abilities:
                abilities.append({**ability, "plugin": plugin.name})
        return abilities

    def get_ability_schema(self, ability_name: str) -> dict | None:
        """Get ability schema for LLM tool calling."""
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
        """Get all ability schemas for LLM."""
        schemas = []
        for ability_name in self._ability_map:
            schema = self.get_ability_schema(ability_name)
            if schema:
                schemas.append(schema)
        return schemas

    def get_ability_owner(self, ability_name: str) -> str | None:
        """Return the plugin name that owns an ability."""
        return self._ability_map.get(ability_name)
