"""
Transport base class.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .protocol import JsonRpcRequest, JsonRpcResponse


class BaseTransport(ABC):
    """Abstract base class for transports."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""

    @abstractmethod
    async def send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send request and wait for response."""

    @abstractmethod
    async def send_notification(self, request: JsonRpcRequest) -> None:
        """Send notification (no response expected)."""

    @abstractmethod
    def receive_notifications(self) -> AsyncIterator[JsonRpcRequest]:
        """Receive incoming notifications from plugin."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
