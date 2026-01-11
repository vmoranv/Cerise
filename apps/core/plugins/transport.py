"""
Transport Layer

Handles communication between Core and Plugin processes.
Supports stdio and HTTP transports.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import aiohttp

from .protocol import JsonRpcError, JsonRpcRequest, JsonRpcResponse

logger = logging.getLogger(__name__)


class BaseTransport(ABC):
    """Abstract base class for transports"""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""

    @abstractmethod
    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request and wait for response"""

    @abstractmethod
    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification (no response expected)"""

    @abstractmethod
    def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """Receive incoming notifications from plugin"""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""


class StdioTransport(BaseTransport):
    """Transport using stdio for subprocess communication"""

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
        """Start subprocess"""
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
            logger.info(f"Started plugin process: {self.command}")
            return True
        except Exception as e:
            logger.exception(f"Failed to start plugin: {e}")
            return False

    async def disconnect(self) -> None:
        """Stop subprocess"""
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
            except Exception:
                pass

        self._process = None
        logger.info("Plugin process stopped")

    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request and wait for response"""
        if not self.is_connected or not self._process or not self._process.stdin:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error("Not connected"),
            )

        # Auto-assign ID if not set
        if request.id is None:
            self._request_id += 1
            request.id = self._request_id

        # Create future for response
        future: asyncio.Future[JsonRpcResponse] = asyncio.Future()
        self._pending[request.id] = future

        try:
            # Write request
            data = json.dumps(request.to_dict()) + "\n"
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()

            # Wait for response
            response = await asyncio.wait_for(future, timeout=self.timeout)
            return response

        except TimeoutError:
            del self._pending[request.id]
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError(-32003, "Request timeout"),
            )
        except Exception as e:
            if request.id in self._pending:
                del self._pending[request.id]
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error(str(e)),
            )

    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification (no response expected)"""
        if not self.is_connected or not self._process or not self._process.stdin:
            return

        request.id = None  # Notifications have no ID
        data = json.dumps(request.to_dict()) + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()

    async def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """Receive incoming notifications"""
        while True:
            notification = await self._notification_queue.get()
            yield notification

    async def _read_loop(self) -> None:
        """Read stdout and dispatch responses/notifications"""
        if not self._process or not self._process.stdout:
            return

        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break

                data = json.loads(line.decode().strip())

                # Check if it's a response or notification
                if "id" in data and data["id"] is not None:
                    # It's a response
                    response = JsonRpcResponse.from_dict(data)
                    if response.id in self._pending:
                        self._pending[response.id].set_result(response)
                        del self._pending[response.id]
                else:
                    # It's a notification from plugin
                    request = JsonRpcRequest.from_dict(data)
                    await self._notification_queue.put(request)

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from plugin: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error reading from plugin: {e}")


class HttpTransport(BaseTransport):
    """Transport using HTTP for plugin communication"""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = headers or {}
        self._session: aiohttp.ClientSession | None = None
        self._request_id = 0
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None

    async def connect(self) -> bool:
        """Create HTTP session"""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers,
            )
            self._connected = True
            logger.info(f"Connected to HTTP plugin: {self.base_url}")
            return True
        except Exception as e:
            logger.exception(f"Failed to connect: {e}")
            return False

    async def disconnect(self) -> None:
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False

    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request via HTTP POST"""
        if not self.is_connected or not self._session:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error("Not connected"),
            )

        if request.id is None:
            self._request_id += 1
            request.id = self._request_id

        try:
            async with self._session.post(
                f"{self.base_url}/rpc",
                json=request.to_dict(),
            ) as resp:
                data = await resp.json()
                return JsonRpcResponse.from_dict(data)

        except TimeoutError:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError(-32003, "Request timeout"),
            )
        except Exception as e:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error(str(e)),
            )

    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification via HTTP POST"""
        if not self.is_connected or not self._session:
            return

        request.id = None
        try:
            await self._session.post(
                f"{self.base_url}/rpc",
                json=request.to_dict(),
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    async def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """HTTP transport doesn't support incoming notifications"""
        # Would need WebSocket for bidirectional communication
        return
        yield  # Make this a generator  # noqa: B027
