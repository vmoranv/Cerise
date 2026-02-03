"""
MCP Config Loader

Loads MCP server configurations from ~/.cerise/mcp.yaml (or mcp.toml).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from .file_utils import load_config_data, resolve_config_path
from .schemas import McpConfig

logger = logging.getLogger(__name__)


class McpConfigLoaderMixin:
    data_dir: Path
    _mcp_config: McpConfig | None

    def load_mcp_config(self) -> McpConfig:
        """Load MCP server configuration."""
        config_path = resolve_config_path(self.data_dir / "mcp.yaml")
        if not config_path.exists():
            self._mcp_config = McpConfig()
            return self._mcp_config

        try:
            data = load_config_data(config_path)
            self._mcp_config = McpConfig(**data)
        except Exception as exc:
            logger.warning("Failed to load mcp config: %s, using defaults", exc)
            self._mcp_config = McpConfig()

        # Expand ${VAR} in env fields.
        for server in self._mcp_config.servers:
            if server.env:
                server.env = _expand_env_vars(server.env)

        return self._mcp_config

    def save_mcp_config(self, config: McpConfig) -> None:
        """Save MCP server configuration."""
        config_path = self.data_dir / "mcp.yaml"
        data = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

        self._mcp_config = config

    def get_mcp_config(self) -> McpConfig:
        """Get cached or load MCP config."""
        if self._mcp_config is None:
            self.load_mcp_config()
        return self._mcp_config  # type: ignore[return-value]


def _expand_env_vars(values: dict[str, str]) -> dict[str, str]:
    """Expand ${VAR} in dict values."""
    expanded: dict[str, str] = {}
    for key, value in values.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            expanded[key] = os.environ.get(env_var, "")
        else:
            expanded[key] = value
    return expanded
