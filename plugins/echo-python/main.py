#!/usr/bin/env python
"""Echo plugin (Python)

A minimal stdio JSON-RPC plugin that exposes a single ability:
- echo_python({text}) -> {text}

Rules:
- stdout is reserved for JSON-RPC messages (one JSON per line)
- write logs to stderr only
"""

from __future__ import annotations

import json
import sys
from typing import Any


def _write(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error(*, req_id: Any, code: int, message: str) -> None:
    _write(
        {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": req_id}
    )


def _result(*, req_id: Any, result: Any) -> None:
    _write({"jsonrpc": "2.0", "result": result, "id": req_id})


def main() -> int:
    config: dict[str, Any] = {}
    permissions: list[str] = []

    abilities = [
        {
            "name": "echo_python",
            "description": "Echo text back (optionally with a prefix from config).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to echo"},
                },
                "required": ["text"],
            },
        }
    ]

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception as exc:
            _write(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                    "id": None,
                }
            )
            continue

        method = str(req.get("method") or "")
        params = req.get("params")
        params = params if isinstance(params, dict) else {}
        req_id = req.get("id")
        is_notification = req_id is None

        try:
            if method == "initialize":
                cfg = params.get("config")
                config = cfg if isinstance(cfg, dict) else {}

                perms = params.get("permissions")
                if isinstance(perms, list):
                    permissions = [
                        str(p) for p in perms if isinstance(p, (str, int, float))
                    ]
                else:
                    permissions = []

                result = {
                    "success": True,
                    "abilities": abilities,
                    "skills": abilities,
                    "tools": abilities,
                }
                if not is_notification:
                    _result(req_id=req_id, result=result)
                continue

            if method == "execute":
                ability = (
                    params.get("ability")
                    or params.get("skill")
                    or params.get("tool")
                    or params.get("name")
                    or ""
                )
                ability = str(ability)

                args = params.get("params")
                if args is None:
                    args = params.get("arguments")
                args = args if isinstance(args, dict) else {}

                ctx = params.get("context")
                ctx = ctx if isinstance(ctx, dict) else {}

                # Example of using config.
                prefix = str(config.get("prefix") or "")

                # Example of consuming permissions passed from Core.
                ctx_perms = ctx.get("permissions")
                if not isinstance(ctx_perms, list):
                    ctx_perms = permissions

                if ability != "echo_python":
                    result = {"success": False, "error": f"Unknown ability: {ability}"}
                else:
                    text = str(args.get("text") or "")
                    result = {
                        "success": True,
                        "data": {"text": f"{prefix}{text}"},
                        "error": None,
                        "emotion_hint": "satisfied",
                    }

                if not is_notification:
                    _result(req_id=req_id, result=result)
                continue

            if method == "health":
                if not is_notification:
                    _result(req_id=req_id, result={"healthy": True})
                continue

            if method == "shutdown":
                if not is_notification:
                    _result(req_id=req_id, result={"success": True})
                break

            if not is_notification:
                _error(req_id=req_id, code=-32601, message="Method not found")

        except Exception as exc:
            if not is_notification:
                _error(req_id=req_id, code=-32603, message=str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
