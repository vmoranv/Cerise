"""A minimal MCP stdio server for tests (JSON-RPC over Content-Length framing)."""

from __future__ import annotations

import json
import sys
from typing import Any


def _read_headers(stream) -> dict[str, str] | None:
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


def _read_message(stream) -> dict[str, Any] | None:
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

    body = stream.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(stream, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stream.write(header + body)
    stream.flush()


def _handle_initialize(req_id: int) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake-mcp-server", "version": "0.0.0"},
        },
    }


def _handle_tools_list(req_id: int) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "echo",
                    "description": "Echo back input text.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
            ],
        },
    }


def _handle_tools_call(req_id: int, params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if name != "echo" or not isinstance(arguments, dict):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": "unknown tool"}], "isError": True},
        }
    text = arguments.get("text", "")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": f"echo:{text}"}], "isError": False},
    }


def main() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        msg = _read_message(stdin)
        if msg is None:
            return 0

        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

        # Ignore notifications.
        if req_id is None:
            continue
        if not isinstance(req_id, int):
            continue

        if method == "initialize":
            _write_message(stdout, _handle_initialize(req_id))
        elif method == "tools/list":
            _write_message(stdout, _handle_tools_list(req_id))
        elif method == "tools/call":
            _write_message(stdout, _handle_tools_call(req_id, params))
        elif method == "ping":
            _write_message(stdout, {"jsonrpc": "2.0", "id": req_id, "result": {}})
        else:
            _write_message(
                stdout,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown method: {method}"},
                },
            )


if __name__ == "__main__":
    raise SystemExit(main())
