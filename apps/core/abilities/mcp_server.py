"""MCP server that exposes Cerise abilities as MCP tools (stdio transport).

This module implements a small subset of MCP's JSON-RPC interface over stdio:
- initialize / initialized
- tools/list
- tools/call

It intentionally does not depend on the API layer so it can be used in different
entry points (API process, CLI process, tests).
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, BinaryIO, Protocol, runtime_checkable

from .base import AbilityContext, AbilityResult

MCP_PROTOCOL_VERSION = "2024-11-05"


@runtime_checkable
class AbilityToolRegistry(Protocol):
    def get_tool_schemas(self) -> list[dict]: ...

    async def execute(self, ability_name: str, params: dict, context: AbilityContext) -> AbilityResult: ...


class McpStdioAbilityServer:
    """Expose abilities as MCP tools over stdio."""

    def __init__(
        self,
        *,
        registry: AbilityToolRegistry,
        allowed_permissions: list[str] | None = None,
        default_user_id: str = "",
        default_session_id: str = "",
    ) -> None:
        self._registry = registry
        self._allowed_permissions = list(allowed_permissions or [])
        self._default_user_id = default_user_id
        self._default_session_id = default_session_id

    def serve_forever(self, *, stdin: BinaryIO | None = None, stdout: BinaryIO | None = None) -> int:
        stdin = stdin or sys.stdin.buffer
        stdout = stdout or sys.stdout.buffer
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            while True:
                message = _read_message(stdin)
                if message is None:
                    return 0
                self._handle_message(loop, stdout, message)
        finally:
            loop.close()

    def _handle_message(self, loop: asyncio.AbstractEventLoop, stdout: BinaryIO, message: dict[str, Any]) -> None:
        req_id = message.get("id")
        method = message.get("method")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}

        # Ignore notifications (no id).
        if req_id is None:
            return
        if not isinstance(req_id, int):
            return

        if method == "initialize":
            _write_message(
                stdout,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "cerise", "version": "0.0.0"},
                    },
                },
            )
            return

        if method == "tools/list":
            tools = self._build_tools()
            _write_message(stdout, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})
            return

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if not isinstance(name, str) or not name:
                _write_message(
                    stdout,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": "Missing tool name"}], "isError": True},
                    },
                )
                return

            context = AbilityContext(
                user_id=self._default_user_id,
                session_id=self._default_session_id,
                permissions=list(self._allowed_permissions),
            )
            try:
                result = loop.run_until_complete(self._registry.execute(name, arguments, context))
            except Exception as exc:
                _write_message(
                    stdout,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True},
                    },
                )
                return

            text, is_error = _ability_result_to_mcp_text(result)
            _write_message(
                stdout,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}], "isError": is_error},
                },
            )
            return

        if method == "ping":
            _write_message(stdout, {"jsonrpc": "2.0", "id": req_id, "result": {}})
            return

        _write_message(
            stdout,
            {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}},
        )

    def _build_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for schema in self._registry.get_tool_schemas():
            fn = schema.get("function") if isinstance(schema, dict) else None
            if not isinstance(fn, dict):
                continue
            name = fn.get("name")
            if not isinstance(name, str) or not name:
                continue
            tools.append(
                {
                    "name": name,
                    "description": fn.get("description") or "",
                    "inputSchema": fn.get("parameters") or {"type": "object", "properties": {}},
                },
            )
        return tools


def _ability_result_to_mcp_text(result: AbilityResult) -> tuple[str, bool]:
    if result.success:
        if result.data is None:
            return "", False
        if isinstance(result.data, (dict, list)):
            return json.dumps(result.data, ensure_ascii=False), False
        return str(result.data), False
    return str(result.error or "Error"), True


def _read_headers(stream: BinaryIO) -> dict[str, str] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        decoded = line.decode("utf-8", errors="replace").strip()
        if decoded == "":
            return headers
        key, _, value = decoded.partition(":")
        headers[key.strip().lower()] = value.strip()


def _read_exact(stream: BinaryIO, length: int) -> bytes:
    data = b""
    while len(data) < length:
        chunk = stream.read(length - len(data))
        if not chunk:
            return b""
        data += chunk
    return data


def _read_message(stream: BinaryIO) -> dict[str, Any] | None:
    headers = _read_headers(stream)
    if headers is None:
        return None
    length_raw = headers.get("content-length")
    if not length_raw:
        return None
    try:
        length = int(length_raw)
    except ValueError:
        return None
    body = _read_exact(stream, length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stream.write(header + body)
    stream.flush()
