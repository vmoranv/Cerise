from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import subprocess
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO

logger = logging.getLogger(__name__)


class JsonRpcClosedError(RuntimeError):
    pass


class JsonRpcProtocolError(RuntimeError):
    pass


class JsonRpcRemoteError(RuntimeError):
    def __init__(self, *, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(f"JSON-RPC error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


@dataclass(frozen=True, slots=True)
class _PendingRequest:
    method: str
    future: asyncio.Future[Any]


class JsonRpcStdioClient:
    """
    Minimal JSON-RPC 2.0 client over stdio using LSP-style Content-Length framing.

    The MCP stdio transport uses the same framing style as LSP:
      Content-Length: <bytes>\\r\\n
      \\r\\n
      <json bytes>
    """

    def __init__(self, *, name: str = "mcp-stdio") -> None:
        self._name = name
        self._proc: subprocess.Popen[bytes] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._next_id = 1
        self._pending: dict[int, _PendingRequest] = {}
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._closed = False

    async def start(
        self,
        *,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        if self._proc is not None:
            return

        args = args or []
        self._loop = asyncio.get_running_loop()
        self._stop.clear()
        self._proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        assert self._proc.stdout is not None  # noqa: S101
        assert self._proc.stdin is not None  # noqa: S101

        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"{self._name}-read",
            daemon=True,
        )
        self._reader_thread.start()

        if self._proc.stderr is not None:
            self._stderr_thread = threading.Thread(
                target=self._stderr_loop,
                name=f"{self._name}-stderr",
                daemon=True,
            )
            self._stderr_thread.start()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop.set()

        for req in list(self._pending.values()):
            if not req.future.done():
                req.future.set_exception(JsonRpcClosedError("JSON-RPC client closed"))
        self._pending.clear()

        if self._proc:
            if self._proc.stdin:
                with contextlib.suppress(Exception):
                    self._proc.stdin.close()
            with contextlib.suppress(Exception):
                self._proc.terminate()
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self._proc.wait, 2)
            self._proc = None

        if self._reader_thread:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self._reader_thread.join, 1)
            self._reader_thread = None
        if self._stderr_thread:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(self._stderr_thread.join, 1)
            self._stderr_thread = None

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self._proc or not self._proc.stdin or not self._proc.stdout or self._closed:
            raise JsonRpcClosedError("JSON-RPC client is not started")

        req_id = self._next_id
        self._next_id += 1

        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params

        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[req_id] = _PendingRequest(method=method, future=fut)
        await self._write_message(payload)

        return await fut

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if not self._proc or not self._proc.stdin or not self._proc.stdout or self._closed:
            raise JsonRpcClosedError("JSON-RPC client is not started")

        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        await self._write_message(payload)

    async def _write_message(self, message: dict[str, Any]) -> None:
        await asyncio.to_thread(self._write_message_sync, message)

    def _write_message_sync(self, message: dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise JsonRpcClosedError("JSON-RPC client is not started")
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        with self._write_lock:
            self._proc.stdin.write(header + body)
            self._proc.stdin.flush()

    def _reader_loop(self) -> None:
        if not self._proc or not self._proc.stdout or not self._loop:
            return
        try:
            while not self._stop.is_set():
                msg = self._read_message_sync(self._proc.stdout)
                if msg is None:
                    return
                self._loop.call_soon_threadsafe(self._handle_message, msg)
        except Exception:
            logger.exception("JSON-RPC reader thread failed (%s)", self._name)
            if self._loop:
                self._loop.call_soon_threadsafe(self._fail_all, JsonRpcClosedError("JSON-RPC reader failed"))

    @staticmethod
    def _read_message_sync(stream: BinaryIO) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = stream.readline()
            if not line:
                return None
            decoded = line.decode("utf-8", errors="replace").strip()
            if decoded == "":
                break
            key, _, value = decoded.partition(":")
            headers[key.strip().lower()] = value.strip()

        length_raw = headers.get("content-length")
        if not length_raw:
            raise JsonRpcProtocolError("Missing Content-Length header")
        try:
            length = int(length_raw)
        except ValueError as exc:  # noqa: PERF203
            raise JsonRpcProtocolError(f"Invalid Content-Length: {length_raw}") from exc

        body = _read_exact(stream, length)
        try:
            decoded_body = body.decode("utf-8")
            return json.loads(decoded_body)
        except Exception as exc:
            raise JsonRpcProtocolError("Invalid JSON-RPC payload") from exc

    def _fail_all(self, exc: Exception) -> None:
        for req in list(self._pending.values()):
            if not req.future.done():
                req.future.set_exception(exc)
        self._pending.clear()

    def _handle_message(self, message: dict[str, Any]) -> None:
        # Notifications are ignored for now.
        if "id" not in message:
            return

        req_id = message.get("id")
        if not isinstance(req_id, int):
            return

        pending = self._pending.pop(req_id, None)
        if not pending:
            return

        if "error" in message and message["error"] is not None:
            err = message["error"]
            if isinstance(err, dict):
                pending.future.set_exception(
                    JsonRpcRemoteError(
                        code=int(err.get("code", -32000)),
                        message=str(err.get("message", "Unknown error")),
                        data=err.get("data"),
                    ),
                )
            else:
                pending.future.set_exception(JsonRpcRemoteError(code=-32000, message=str(err)))
            return

        pending.future.set_result(message.get("result"))

    def _stderr_loop(self) -> None:
        if not self._proc or not self._proc.stderr:
            return
        try:
            while not self._stop.is_set():
                line = self._proc.stderr.readline()
                if not line:
                    return
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.debug("[%s] stderr: %s", self._name, text)
        except Exception:
            logger.exception("stderr reader failed (%s)", self._name)


def _read_exact(stream: BinaryIO, length: int) -> bytes:
    data = b""
    while len(data) < length:
        chunk = stream.read(length - len(data))
        if not chunk:
            raise JsonRpcClosedError("EOF while reading body")
        data += chunk
    return data
