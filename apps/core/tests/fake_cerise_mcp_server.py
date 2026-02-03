"""Fake Cerise MCP server process for tests.

Runs the real `McpStdioAbilityServer` and registers a single demo ability.
"""

from __future__ import annotations

from apps.core.abilities.base import AbilityCategory, AbilityContext, AbilityResult, AbilityType, BaseAbility
from apps.core.abilities.mcp_server import McpStdioAbilityServer
from apps.core.abilities.registry import AbilityRegistry


class EchoAbility(BaseAbility):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def display_name(self) -> str:
        return "Echo"

    @property
    def description(self) -> str:
        return "Echo back input text."

    @property
    def ability_type(self) -> AbilityType:
        return AbilityType.BUILTIN

    @property
    def category(self) -> AbilityCategory:
        return AbilityCategory.UTILITY

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }

    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:  # noqa: ARG002
        text = params.get("text", "")
        return AbilityResult(success=True, data=f"echo:{text}")


def main() -> int:
    AbilityRegistry.register(EchoAbility())
    server = McpStdioAbilityServer(registry=AbilityRegistry, allowed_permissions=[])
    return server.serve_forever()


if __name__ == "__main__":
    raise SystemExit(main())
