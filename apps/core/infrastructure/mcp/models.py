from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class McpTool:
    """A MCP tool definition as returned by `tools/list`."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class McpServerConfig:
    """Connection parameters for a stdio MCP server."""

    id: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    enabled: bool = True
    tool_name_prefix: str | None = None
