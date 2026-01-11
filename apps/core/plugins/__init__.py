# Cross-Language Plugin System

"""
Plugin system using JSON-RPC 2.0 for cross-language support.
Plugins run as separate processes.
"""

from .bridge import PluginBridge
from .installer import PluginInstaller
from .manager import PluginManager
from .protocol import (
    ExecuteParams,
    ExecuteResult,
    InitializeParams,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
)
from .transport import HttpTransport, StdioTransport

__all__ = [
    "PluginManager",
    "PluginBridge",
    "PluginInstaller",
    "StdioTransport",
    "HttpTransport",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "InitializeParams",
    "ExecuteParams",
    "ExecuteResult",
]

__all__ = [
    "PluginManager",
    "PluginBridge",
    "StdioTransport",
    "HttpTransport",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "InitializeParams",
    "ExecuteParams",
    "ExecuteResult",
]
