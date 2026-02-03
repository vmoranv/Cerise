"""MCP integration tests (stdio)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from apps.core.abilities.base import AbilityContext
from apps.core.abilities.mcp_manager import McpManager
from apps.core.infrastructure.mcp import McpServerConfig


class DummyRegistry:
    def __init__(self) -> None:
        self.abilities = {}

    def register(self, ability) -> None:
        self.abilities[ability.name] = ability


@pytest.mark.asyncio
async def test_mcp_manager_registers_tools_and_executes() -> None:
    server_script = Path(__file__).with_name("fake_mcp_server.py")
    registry = DummyRegistry()

    manager = McpManager(
        servers=[
            McpServerConfig(
                id="fake-server",
                command=sys.executable,
                args=[str(server_script)],
                env=None,
                enabled=True,
                tool_name_prefix=None,
            ),
        ],
    )

    try:
        await manager.load_and_register(registry=registry)

        assert "mcp_fake-server_echo" in registry.abilities
        ability = registry.abilities["mcp_fake-server_echo"]

        context = AbilityContext(user_id="u", session_id="s", permissions=[])
        result = await ability.execute({"text": "hi"}, context)
        assert result.success is True
        assert result.data == "echo:hi"
    finally:
        await manager.close()
