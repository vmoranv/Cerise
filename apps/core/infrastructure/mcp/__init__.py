"""
Model Context Protocol (MCP) transport helpers.

This module intentionally implements a small, dependency-free subset of MCP
over stdio, sufficient for listing tools and calling tools.
"""

from .models import McpServerConfig, McpTool
from .stdio_client import McpStdioClient

__all__ = [
    "McpServerConfig",
    "McpTool",
    "McpStdioClient",
]
