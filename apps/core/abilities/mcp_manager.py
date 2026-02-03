from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from ..infrastructure.mcp import McpServerConfig, McpStdioClient, McpTool
from .base import AbilityCategory, AbilityContext, AbilityResult, AbilityType, BaseAbility

logger = logging.getLogger(__name__)

_INVALID_TOOL_CHARS = re.compile(r"[^a-zA-Z0-9_-]+")


def _sanitize_tool_component(value: str) -> str:
    cleaned = _INVALID_TOOL_CHARS.sub("_", value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "tool"


def _limit_tool_name(name: str, *, max_len: int = 64) -> str:
    if len(name) <= max_len:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    keep = max_len - (len(digest) + 1)
    return f"{name[:keep]}_{digest}"


def _mcp_call_result_to_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if not isinstance(result, dict):
        return str(result)

    content = result.get("content")
    if not isinstance(content, list):
        return str(result)

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    if parts:
        return "\n".join(parts)
    return str(result)


class McpToolAbility(BaseAbility):
    def __init__(
        self,
        *,
        ability_name: str,
        display_name: str,
        tool: McpTool,
        client: McpStdioClient,
    ) -> None:
        self._ability_name = ability_name
        self._display_name = display_name
        self._tool = tool
        self._client = client

    @property
    def name(self) -> str:
        return self._ability_name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def description(self) -> str:
        if self._tool.description:
            return f"[MCP:{self._client.server_id}] {self._tool.description}"
        return f"[MCP:{self._client.server_id}] {self._tool.name}"

    @property
    def ability_type(self) -> AbilityType:
        return AbilityType.PLUGIN

    @property
    def category(self) -> AbilityCategory:
        return AbilityCategory.UTILITY

    @property
    def parameters_schema(self) -> dict:
        schema = self._tool.input_schema or {}
        if isinstance(schema, dict) and schema:
            return schema
        return {"type": "object", "properties": {}}

    async def execute(self, params: dict, context: AbilityContext) -> AbilityResult:
        try:
            raw = await self._client.call_tool(self._tool.name, params)
        except Exception as exc:
            return AbilityResult(success=False, error=str(exc))

        if isinstance(raw, dict) and raw.get("isError") is True:
            return AbilityResult(success=False, error=_mcp_call_result_to_text(raw), data=raw)

        return AbilityResult(success=True, data=_mcp_call_result_to_text(raw))


class McpManager:
    """Loads MCP servers and registers tools as Cerise abilities."""

    def __init__(self, *, servers: list[McpServerConfig]) -> None:
        self._servers = servers
        self._clients: dict[str, McpStdioClient] = {}
        self._registered: list[str] = []

    @property
    def registered_abilities(self) -> list[str]:
        return list(self._registered)

    async def load_and_register(self, *, registry) -> None:
        for server in self._servers:
            if not server.enabled:
                continue
            try:
                client = McpStdioClient(server=server)
                tools = await client.list_tools()
            except Exception:
                logger.exception("Failed to initialize MCP server '%s'", server.id)
                continue

            self._clients[server.id] = client

            for tool in tools:
                ability_name = self._build_ability_name(server, tool)
                display_name = f"{tool.name} (MCP:{server.id})"
                registry.register(
                    McpToolAbility(
                        ability_name=ability_name,
                        display_name=display_name,
                        tool=tool,
                        client=client,
                    ),
                )
                self._registered.append(ability_name)

    async def close(self) -> None:
        for client in self._clients.values():
            try:
                await client.close()
            except Exception:
                logger.exception("Failed to close MCP client")
        self._clients.clear()

    def _build_ability_name(self, server: McpServerConfig, tool: McpTool) -> str:
        prefix = server.tool_name_prefix or f"mcp_{_sanitize_tool_component(server.id)}__"
        safe_prefix = _sanitize_tool_component(prefix)
        if not safe_prefix.endswith("_"):
            safe_prefix = f"{safe_prefix}_"
        safe_tool = _sanitize_tool_component(tool.name)
        return _limit_tool_name(f"{safe_prefix}{safe_tool}")
