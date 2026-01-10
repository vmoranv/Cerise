"""
WebSocket 连接管理器测试
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.websocket.manager import ConnectionManager


class TestConnectionManager:
    """连接管理器测试"""

    @pytest.fixture
    def manager(self) -> ConnectionManager:
        """创建管理器"""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self) -> MagicMock:
        """创建 Mock WebSocket"""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        ws.send_bytes = AsyncMock()
        ws.send_json = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试连接"""
        client_id = await manager.connect(mock_websocket)

        assert client_id is not None
        assert client_id in manager.active_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_client_id(
        self, manager: ConnectionManager, mock_websocket: MagicMock
    ):
        """测试使用指定 client_id 连接"""
        client_id = await manager.connect(mock_websocket, client_id="test-client")

        assert client_id == "test-client"
        assert "test-client" in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试断开连接"""
        client_id = await manager.connect(mock_websocket)

        await manager.disconnect(client_id)

        assert client_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager: ConnectionManager):
        """测试断开不存在的连接"""
        # 应该不抛出异常
        await manager.disconnect("nonexistent-client")

    @pytest.mark.asyncio
    async def test_send_text(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试发送文本"""
        client_id = await manager.connect(mock_websocket)

        await manager.send_text(client_id, "Hello")

        mock_websocket.send_text.assert_called_with("Hello")

    @pytest.mark.asyncio
    async def test_send_bytes(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试发送字节"""
        client_id = await manager.connect(mock_websocket)

        await manager.send_bytes(client_id, b"binary_data")

        mock_websocket.send_bytes.assert_called_with(b"binary_data")

    @pytest.mark.asyncio
    async def test_send_json(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试发送 JSON"""
        client_id = await manager.connect(mock_websocket)
        data = {"type": "response", "data": "test"}

        await manager.send_json(client_id, data)

        mock_websocket.send_json.assert_called_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_text(self, manager: ConnectionManager):
        """测试广播文本"""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_text = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(ws1, client_id="client1")
        await manager.connect(ws2, client_id="client2")

        await manager.broadcast_text("Hello everyone")

        ws1.send_text.assert_called_with("Hello everyone")
        ws2.send_text.assert_called_with("Hello everyone")

    @pytest.mark.asyncio
    async def test_broadcast_json(self, manager: ConnectionManager):
        """测试广播 JSON"""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = MagicMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect(ws1, client_id="client1")
        await manager.connect(ws2, client_id="client2")

        data = {"type": "broadcast", "message": "test"}
        await manager.broadcast_json(data)

        ws1.send_json.assert_called_with(data)
        ws2.send_json.assert_called_with(data)

    def test_get_connection_count(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试获取连接数"""
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_get_connection_count_after_connect(self, manager: ConnectionManager):
        """测试连接后获取连接数"""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()

        await manager.connect(ws1)
        assert manager.get_connection_count() == 1

        await manager.connect(ws2)
        assert manager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_is_connected(self, manager: ConnectionManager, mock_websocket: MagicMock):
        """测试检查连接状态"""
        assert not manager.is_connected("test-client")

        await manager.connect(mock_websocket, client_id="test-client")
        assert manager.is_connected("test-client")

        await manager.disconnect("test-client")
        assert not manager.is_connected("test-client")

    @pytest.mark.asyncio
    async def test_get_all_client_ids(self, manager: ConnectionManager):
        """测试获取所有客户端 ID"""
        ws1 = MagicMock()
        ws1.accept = AsyncMock()
        ws2 = MagicMock()
        ws2.accept = AsyncMock()

        await manager.connect(ws1, client_id="client1")
        await manager.connect(ws2, client_id="client2")

        client_ids = manager.get_all_client_ids()

        assert "client1" in client_ids
        assert "client2" in client_ids
        assert len(client_ids) == 2
