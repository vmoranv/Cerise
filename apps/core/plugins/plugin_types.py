"""
Plugin manager types.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .transport import BaseTransport


def normalize_abilities(abilities: list[dict] | None) -> list[dict]:
    """Normalize ability/tool definitions for downstream tool schemas."""
    if not abilities:
        return []

    normalized: list[dict] = []
    for entry in abilities:
        if not isinstance(entry, dict):
            continue
        ability = dict(entry)
        if "parameters" not in ability:
            input_schema = ability.get("inputSchema") or ability.get("input_schema")
            if input_schema is not None:
                ability["parameters"] = input_schema
        normalized.append(ability)
    return normalized


@dataclass
class PluginManifest:
    """Plugin manifest data."""

    name: str
    version: str
    display_name: str = ""
    description: str = ""
    author: str = ""

    language: str = "python"
    entry: str = "main.py"
    command: str = ""
    transport: str = "stdio"
    http_url: str = ""

    abilities: list[dict] = field(default_factory=list)

    permissions: list[str] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        runtime = data.get("runtime", {})
        abilities = data.get("abilities")
        skills = data.get("skills")
        tools = data.get("tools")
        mcp_block = data.get("mcp")
        if not tools and isinstance(mcp_block, dict):
            tools = mcp_block.get("tools")
        if not abilities:
            abilities = skills or tools
        abilities = normalize_abilities(abilities)
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
            abilities=abilities,
            permissions=data.get("permissions", []),
            config_schema=data.get("config_schema", {}),
        )


@dataclass
class LoadedPlugin:
    """Represents a loaded plugin."""

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
