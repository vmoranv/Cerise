"""
JSON-RPC 2.0 Protocol

Defines the protocol for communication between Core and Plugins.
"""

from .jsonrpc import ErrorCode, JsonRpcError, JsonRpcRequest, JsonRpcResponse  # noqa: F401
from .protocol_types import (  # noqa: F401
    ExecuteParams,
    ExecuteResult,
    HealthResult,
    InitializeParams,
    InitializeResult,
    Methods,
)

__all__ = [
    "ErrorCode",
    "JsonRpcError",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "InitializeParams",
    "InitializeResult",
    "ExecuteParams",
    "ExecuteResult",
    "HealthResult",
    "Methods",
]
