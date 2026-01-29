"""Health checks for WebSocket connections."""

from __future__ import annotations

from datetime import datetime


class ConnectionManagerHealthMixin:
    """Health check helpers for connection manager."""

    async def ping_all(self) -> dict[str, bool]:
        """Ping all connections to verify activity."""
        results: dict[str, bool] = {}

        for conn_id, conn_info in list(self._connections.items()):
            try:
                await conn_info.websocket.send_json({"type": "ping"})
                results[conn_id] = True
            except Exception:
                results[conn_id] = False

        return results

    async def cleanup_stale_connections(self, max_idle_seconds: int = 300) -> int:
        """Disconnect idle connections."""
        now = datetime.now()
        stale_connections = []

        for conn_id, conn_info in self._connections.items():
            idle_time = (now - conn_info.last_active).total_seconds()
            if idle_time > max_idle_seconds:
                stale_connections.append(conn_id)

        for conn_id in stale_connections:
            await self.disconnect(conn_id, code=1000, reason="Idle timeout")

        return len(stale_connections)
