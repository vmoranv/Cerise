"""WebSocket 连接管理器测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.websocket.manager import ConnectionManager


class TestConnectionManager:
    """连接管理器测试"""

    @pytest.fixture
    def manager(self) -> ConnectionManager:
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(
        self, manager: ConnectionManager, mock_websocket: MagicMock
    ):
        conn_id = await manager.connect(mock_websocket, connection_id="client-1")
        assert conn_id == "client-1"
        assert manager.connection_count == 1
        assert manager.get_connection(conn_id) is not None

        await manager.disconnect(conn_id)
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_send_json(self, manager: ConnectionManager, mock_websocket: MagicMock):
        conn_id = await manager.connect(mock_websocket)
        ok = await manager.send_json(conn_id, {"type": "ping"})
        assert ok is True
        mock_websocket.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_bytes(self, manager: ConnectionManager, mock_websocket: MagicMock):
        conn_id = await manager.connect(mock_websocket)
        ok = await manager.send_bytes(conn_id, b"data")
        assert ok is True
        mock_websocket.send_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_text(self, manager: ConnectionManager, mock_websocket: MagicMock):
        conn_id = await manager.connect(mock_websocket)
        ok = await manager.send_text(conn_id, "hello")
        assert ok is True
        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_json(self, manager: ConnectionManager):
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, connection_id="client1")
        await manager.connect(ws2, connection_id="client2")

        count = await manager.broadcast_json({"type": "broadcast"})
        assert count == 2

    def test_group_management(self, manager: ConnectionManager, mock_websocket: MagicMock):
        manager._connections["client1"] = MagicMock()
        manager.add_to_group("client1", "group")
        assert "client1" in manager.get_group_members("group")
        manager.remove_from_group("client1", "group")
        assert "client1" not in manager.get_group_members("group")
