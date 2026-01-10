"""
WebSocket 处理器测试
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.websocket.handler import WebSocketHandler


class TestWebSocketHandler:
    """WebSocket 处理器测试"""

    @pytest.fixture
    def mock_tts_adapter(self) -> MagicMock:
        """创建 Mock TTS 适配器"""
        adapter = MagicMock()
        adapter.synthesize = AsyncMock(return_value=b"audio_data")
        adapter.synthesize_stream = AsyncMock()
        adapter.get_available_characters = MagicMock(return_value=["mika", "feibi"])
        return adapter

    @pytest.fixture
    def mock_asr_engine(self) -> MagicMock:
        """创建 Mock ASR 引擎"""
        engine = MagicMock()
        engine.transcribe = AsyncMock(
            return_value=MagicMock(
                text="测试文本",
                language="zh",
                confidence=0.95,
                duration=1.5,
            )
        )
        engine.transcribe_stream = AsyncMock()
        engine.is_initialized = MagicMock(return_value=True)
        return engine

    @pytest.fixture
    def mock_connection_manager(self) -> MagicMock:
        """创建 Mock 连接管理器"""
        manager = MagicMock()
        manager.send_json = AsyncMock()
        manager.send_bytes = AsyncMock()
        manager.send_text = AsyncMock()
        return manager

    @pytest.fixture
    def handler(
        self,
        mock_tts_adapter: MagicMock,
        mock_asr_engine: MagicMock,
        mock_connection_manager: MagicMock,
    ) -> WebSocketHandler:
        """创建处理器"""
        return WebSocketHandler(
            tts_adapter=mock_tts_adapter,
            asr_engine=mock_asr_engine,
            connection_manager=mock_connection_manager,
        )

    @pytest.mark.asyncio
    async def test_handle_tts_request(
        self,
        handler: WebSocketHandler,
        mock_tts_adapter: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试处理 TTS 请求"""
        message = {
            "type": "tts",
            "text": "你好世界",
            "character": "mika",
        }

        await handler.handle_message("client1", message)

        mock_tts_adapter.synthesize.assert_called_once()
        mock_connection_manager.send_bytes.assert_called()

    @pytest.mark.asyncio
    async def test_handle_asr_request(
        self,
        handler: WebSocketHandler,
        mock_asr_engine: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试处理 ASR 请求"""
        audio_data = b"audio_bytes"
        message = {
            "type": "asr",
            "audio": audio_data.hex(),  # 以十六进制发送
        }

        await handler.handle_message("client1", message)

        mock_asr_engine.transcribe.assert_called_once()
        mock_connection_manager.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_handle_ping(
        self,
        handler: WebSocketHandler,
        mock_connection_manager: MagicMock,
    ):
        """测试处理 ping 消息"""
        message = {"type": "ping"}

        await handler.handle_message("client1", message)

        mock_connection_manager.send_json.assert_called_with("client1", {"type": "pong"})

    @pytest.mark.asyncio
    async def test_handle_get_characters(
        self,
        handler: WebSocketHandler,
        mock_tts_adapter: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试获取可用角色列表"""
        message = {"type": "get_characters"}

        await handler.handle_message("client1", message)

        mock_tts_adapter.get_available_characters.assert_called_once()
        mock_connection_manager.send_json.assert_called()

        # 检查发送的响应
        call_args = mock_connection_manager.send_json.call_args
        response = call_args[0][1]
        assert response["type"] == "characters"
        assert "characters" in response

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(
        self,
        handler: WebSocketHandler,
        mock_connection_manager: MagicMock,
    ):
        """测试处理未知消息类型"""
        message = {"type": "unknown_type"}

        await handler.handle_message("client1", message)

        # 应该发送错误响应
        mock_connection_manager.send_json.assert_called()
        call_args = mock_connection_manager.send_json.call_args
        response = call_args[0][1]
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_invalid_message(
        self,
        handler: WebSocketHandler,
        mock_connection_manager: MagicMock,
    ):
        """测试处理无效消息"""
        message = {"invalid": "message"}  # 缺少 type 字段

        await handler.handle_message("client1", message)

        mock_connection_manager.send_json.assert_called()
        call_args = mock_connection_manager.send_json.call_args
        response = call_args[0][1]
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_tts_with_options(
        self,
        handler: WebSocketHandler,
        mock_tts_adapter: MagicMock,
    ):
        """测试带选项的 TTS 请求"""
        message = {
            "type": "tts",
            "text": "测试",
            "character": "feibi",
            "speed": 1.2,
            "pitch": 0.9,
        }

        await handler.handle_message("client1", message)

        mock_tts_adapter.synthesize.assert_called_once()
        call_args = mock_tts_adapter.synthesize.call_args
        # 验证参数传递
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_handle_asr_error(
        self,
        handler: WebSocketHandler,
        mock_asr_engine: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试 ASR 错误处理"""
        mock_asr_engine.transcribe.side_effect = Exception("ASR error")

        message = {
            "type": "asr",
            "audio": b"audio".hex(),
        }

        await handler.handle_message("client1", message)

        # 应该发送错误响应
        mock_connection_manager.send_json.assert_called()
        call_args = mock_connection_manager.send_json.call_args
        response = call_args[0][1]
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_tts_error(
        self,
        handler: WebSocketHandler,
        mock_tts_adapter: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试 TTS 错误处理"""
        mock_tts_adapter.synthesize.side_effect = Exception("TTS error")

        message = {
            "type": "tts",
            "text": "测试",
        }

        await handler.handle_message("client1", message)

        # 应该发送错误响应
        mock_connection_manager.send_json.assert_called()
        call_args = mock_connection_manager.send_json.call_args
        response = call_args[0][1]
        assert response["type"] == "error"

    @pytest.mark.asyncio
    async def test_handle_stream_tts_request(
        self,
        handler: WebSocketHandler,
        mock_tts_adapter: MagicMock,
        mock_connection_manager: MagicMock,
    ):
        """测试流式 TTS 请求"""

        # 设置流式返回
        async def mock_stream():
            yield b"chunk1"
            yield b"chunk2"
            yield b"chunk3"

        mock_tts_adapter.synthesize_stream.return_value = mock_stream()

        message = {
            "type": "tts_stream",
            "text": "流式测试",
        }

        await handler.handle_message("client1", message)

        mock_tts_adapter.synthesize_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_json_message(self, handler: WebSocketHandler):
        """测试解析 JSON 消息"""
        json_str = '{"type": "ping"}'

        result = handler.parse_message(json_str)

        assert result == {"type": "ping"}

    def test_parse_invalid_json(self, handler: WebSocketHandler):
        """测试解析无效 JSON"""
        invalid_json = "not valid json"

        result = handler.parse_message(invalid_json)

        assert result is None or "error" in result.get("type", "")
