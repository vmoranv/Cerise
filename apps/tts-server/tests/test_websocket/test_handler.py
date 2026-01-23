"""WebSocket 处理器测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import ServerConfig
from src.websocket.handler import WebSocketHandler
from src.websocket.types import MessageType


class TestWebSocketHandler:
    """WebSocket 处理器测试"""

    @pytest.fixture
    def manager(self) -> MagicMock:
        manager = MagicMock()
        manager.send_json = AsyncMock()
        manager.send_bytes = AsyncMock()
        manager.update_connection = MagicMock()
        manager.connect = AsyncMock(return_value="conn-1")
        manager.disconnect = AsyncMock()
        return manager

    @pytest.fixture
    def handler(self, manager: MagicMock) -> WebSocketHandler:
        tts_synthesize = AsyncMock(return_value=b"audio_data")
        asr_engine = MagicMock()
        return WebSocketHandler(
            ServerConfig(), manager, asr_engine=asr_engine, tts_synthesize=tts_synthesize
        )

    @pytest.mark.asyncio
    async def test_handle_ping(self, handler: WebSocketHandler, manager: MagicMock):
        await handler._process_message("conn-1", {"type": MessageType.PING})
        manager.send_json.assert_called_once()
        response = manager.send_json.call_args[0][1]
        assert response["type"] == MessageType.PONG

    @pytest.mark.asyncio
    async def test_handle_asr_start(self, handler: WebSocketHandler, manager: MagicMock):
        await handler._process_message("conn-1", {"type": MessageType.ASR_START, "language": "zh"})
        manager.send_json.assert_called_once()
        response = manager.send_json.call_args[0][1]
        assert response["type"] == "asr_ready"

    @pytest.mark.asyncio
    async def test_handle_tts_request(self, handler: WebSocketHandler, manager: MagicMock):
        await handler._process_message(
            "conn-1",
            {"type": MessageType.TTS_REQUEST, "text": "你好", "character": "mika", "stream": False},
        )
        manager.send_bytes.assert_called_once()
        manager.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_unknown_type(self, handler: WebSocketHandler, manager: MagicMock):
        await handler._process_message("conn-1", {"type": "unknown"})
        manager.send_json.assert_called_once()
        response = manager.send_json.call_args[0][1]
        assert response["type"] == MessageType.ERROR
