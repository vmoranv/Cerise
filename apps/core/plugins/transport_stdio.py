"""
Stdio transport implementation.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from .protocol import JsonRpcError, JsonRpcRequest, JsonRpcResponse
from .transport_base import BaseTransport

logger = logging.getLogger(__name__)


class StdioTransport(BaseTransport):
    """Transport using stdio for subprocess communication."""

    def __init__(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.timeout = timeout

        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int | str, asyncio.Future[JsonRpcResponse]] = {}
        self._reader_task: asyncio.Task | None = None
        self._notification_queue: asyncio.Queue[JsonRpcRequest] = asyncio.Queue()

    @property
    def is_connected(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def connect(self) -> bool:
        """Start subprocess."""
        try:
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            logger.info("Started plugin process: %s", self.command)
            return True
        except Exception as exc:
            logger.exception("Failed to start plugin: %s", exc)
            return False

    async def disconnect(self) -> None:
        """Stop subprocess."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                self._process.kill()
            except Exception as exc:
                logger.debug("Failed to stop plugin process (%s): %s", self.command, exc)

        self._process = None
        logger.info("Plugin process stopped")

    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request and wait for response."""
        if not self.is_connected or not self._process or not self._process.stdin:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error("Not connected"),
            )

        if request.id is None:
            self._request_id += 1
            request.id = self._request_id

        future: asyncio.Future[JsonRpcResponse] = asyncio.Future()
        self._pending[request.id] = future

        try:
            data = json.dumps(request.to_dict()) + "\n"
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()

            response = await asyncio.wait_for(future, timeout=self.timeout)
            return response

        except TimeoutError:
            del self._pending[request.id]
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError(-32003, "Request timeout"),
            )
        except Exception as exc:
            if request.id in self._pending:
                del self._pending[request.id]
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error(str(exc)),
            )

    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification (no response expected)."""
        if not self.is_connected or not self._process or not self._process.stdin:
            return

        request.id = None
        data = json.dumps(request.to_dict()) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

    async def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """Receive incoming notifications."""
        while True:
            notification = await self._notification_queue.get()
            yield notification

    async def _read_loop(self) -> None:
        """Read stdout and dispatch responses/notifications."""
        if not self._process or not self._process.stdout:
            return

        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break

                data = json.loads(line.decode().strip())

                if "id" in data and data["id"] is not None:
                    response = JsonRpcResponse.from_dict(data)
                    if response.id in self._pending:
                        self._pending[response.id].set_result(response)
                        del self._pending[response.id]
                else:
                    request = JsonRpcRequest.from_dict(data)
                    await self._notification_queue.put(request)

            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON from plugin: %s", exc)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Error reading from plugin: %s", exc)
