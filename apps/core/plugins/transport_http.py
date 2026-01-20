"""
HTTP transport implementation.
"""

import logging
from collections.abc import AsyncIterator

import aiohttp

from .protocol import JsonRpcError, JsonRpcRequest, JsonRpcResponse
from .transport_base import BaseTransport

logger = logging.getLogger(__name__)


class HttpTransport(BaseTransport):
    """Transport using HTTP for plugin communication."""

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
        """Create HTTP session."""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers=self.headers,
            )
            self._connected = True
            logger.info("Connected to HTTP plugin: %s", self.base_url)
            return True
        except Exception as exc:
            logger.exception("Failed to connect: %s", exc)
            return False

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False

    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request via HTTP POST."""
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
        except Exception as exc:
            return JsonRpcResponse.failure(
                request.id,
                JsonRpcError.internal_error(str(exc)),
            )

    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification via HTTP POST."""
        if not self.is_connected or not self._session:
            return

        request.id = None
        try:
            await self._session.post(
                f"{self.base_url}/rpc",
                json=request.to_dict(),
            )
        except Exception as exc:
            logger.warning("Failed to send notification: %s", exc)

    async def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """HTTP transport doesn't support incoming notifications."""
        return
        yield  # Make this a generator  # noqa: B027
