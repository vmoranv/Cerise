"""MCP server tests (stdio)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from apps.core.infrastructure.mcp import McpServerConfig, McpStdioClient


@pytest.mark.asyncio
async def test_mcp_stdio_server_exposes_cerise_abilities() -> None:
    server_script = Path(__file__).with_name("fake_cerise_mcp_server.py")
    client = McpStdioClient(
        server=McpServerConfig(
            id="cerise-test",
            command=sys.executable,
            args=[str(server_script)],
            env=None,
            enabled=True,
            tool_name_prefix=None,
        ),
    )

    try:
        tools = await client.list_tools()
        assert any(t.name == "echo" for t in tools)

        result = await client.call_tool("echo", {"text": "hi"})
        assert isinstance(result, dict)
        assert result.get("isError") is False

        content = result.get("content")
        assert isinstance(content, list)
        text = content[0].get("text") if content and isinstance(content[0], dict) else None
        assert text == "echo:hi"
    finally:
        await client.close()
