"""
JSON-RPC 2.0 Protocol

Defines the protocol for communication between Core and Plugins.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """JSON-RPC 2.0 error codes"""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom error codes (-32000 to -32099)
    PLUGIN_NOT_READY = -32000
    ABILITY_NOT_FOUND = -32001
    PERMISSION_DENIED = -32002
    EXECUTION_TIMEOUT = -32003
    PLUGIN_ERROR = -32010


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 Error object"""

    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def parse_error(cls) -> "JsonRpcError":
        return cls(ErrorCode.PARSE_ERROR, "Parse error")

    @classmethod
    def invalid_request(cls) -> "JsonRpcError":
        return cls(ErrorCode.INVALID_REQUEST, "Invalid Request")

    @classmethod
    def method_not_found(cls, method: str) -> "JsonRpcError":
        return cls(ErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}")

    @classmethod
    def invalid_params(cls, message: str = "Invalid params") -> "JsonRpcError":
        return cls(ErrorCode.INVALID_PARAMS, message)

    @classmethod
    def internal_error(cls, message: str = "Internal error") -> "JsonRpcError":
        return cls(ErrorCode.INTERNAL_ERROR, message)


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 Request"""

    method: str
    params: dict | list | None = None
    id: int | str | None = None  # None for notifications
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict:
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "JsonRpcRequest":
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )

    def is_notification(self) -> bool:
        return self.id is None


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 Response"""

    id: int | str | None
    result: Any = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict:
        response = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            response["error"] = self.error.to_dict()
        else:
            response["result"] = self.result
        return response

    @classmethod
    def from_dict(cls, data: dict) -> "JsonRpcResponse":
        error = None
        if "error" in data:
            err = data["error"]
            error = JsonRpcError(
                code=err.get("code", ErrorCode.INTERNAL_ERROR),
                message=err.get("message", "Unknown error"),
                data=err.get("data"),
            )
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", "2.0"),
        )

    @classmethod
    def success(cls, id: int | str, result: Any) -> "JsonRpcResponse":
        return cls(id=id, result=result)

    @classmethod
    def failure(cls, id: int | str | None, error: JsonRpcError) -> "JsonRpcResponse":
        return cls(id=id, error=error)


# ----- Method-specific parameter and result types -----


@dataclass
class InitializeParams:
    """Parameters for 'initialize' method"""

    plugin_name: str
    config: dict = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)


@dataclass
class InitializeResult:
    """Result for 'initialize' method"""

    success: bool
    abilities: list[dict] = field(default_factory=list)
    error: str | None = None


@dataclass
class ExecuteParams:
    """Parameters for 'execute' method"""

    ability: str
    params: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)


@dataclass
class ExecuteResult:
    """Result for 'execute' method"""

    success: bool
    data: Any = None
    error: str | None = None
    emotion_hint: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "emotion_hint": self.emotion_hint,
        }


@dataclass
class HealthResult:
    """Result for 'health' method"""

    healthy: bool
    message: str = ""


# Method constants
class Methods:
    """Standard method names"""

    INITIALIZE = "initialize"
    EXECUTE = "execute"
    HEALTH = "health"
    SHUTDOWN = "shutdown"

    # Plugin → Core notifications
    EVENT = "event"
    LOG = "log"
