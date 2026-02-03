from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from .jsonrpc_stdio import JsonRpcStdioClient
from .models import McpServerConfig, McpTool

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"


class McpStdioClient:
    """Minimal MCP client for stdio servers."""

    def __init__(self, *, server: McpServerConfig) -> None:
        self._server = server
        self._rpc = JsonRpcStdioClient(name=f"mcp:{server.id}")
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def server_id(self) -> str:
        return self._server.id

    async def start(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            await self._rpc.start(command=self._server.command, args=self._server.args, env=self._server.env)
            await self._rpc.request(
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "cerise", "version": "0.0.0"},
                },
            )
            with contextlib.suppress(Exception):
                await self._rpc.notify("initialized")
            self._initialized = True

    async def close(self) -> None:
        await self._rpc.close()

    async def list_tools(self) -> list[McpTool]:
        await self.start()
        result = await self._rpc.request("tools/list", {})
        tools: list[McpTool] = []
        if isinstance(result, dict):
            raw_tools = result.get("tools", [])
            if isinstance(raw_tools, list):
                for item in raw_tools:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name", "")).strip()
                    if not name:
                        continue
                    tools.append(
                        McpTool(
                            name=name,
                            description=item.get("description"),
                            input_schema=item.get("inputSchema") or {},
                        ),
                    )
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        await self.start()
        return await self._rpc.request("tools/call", {"name": tool_name, "arguments": arguments or {}})
