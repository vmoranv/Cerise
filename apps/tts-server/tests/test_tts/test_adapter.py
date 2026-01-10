"""
TTS 适配器测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import TTSConfig
from src.tts.adapter import TTSAdapter, TTSRequest, TTSResponse


class TestTTSRequest:
    """TTS 请求测试"""

    def test_create_request(self):
        """测试创建请求"""
        request = TTSRequest(
            text="你好世界",
            character_name="mika",
            language="zh",
        )
        assert request.text == "你好世界"
        assert request.character_name == "mika"
        assert request.language == "zh"

    def test_request_with_defaults(self):
        """测试默认值"""
        request = TTSRequest(text="hello")
        assert request.text == "hello"
        assert request.character_name is None
        assert request.language is None

    def test_request_with_all_options(self):
        """测试所有选项"""
        request = TTSRequest(
            text="测试",
            character_name="feibi",
            language="zh",
            speed=1.2,
            pitch=0.9,
        )
        assert request.speed == 1.2
        assert request.pitch == 0.9


class TestTTSResponse:
    """TTS 响应测试"""

    def test_create_response(self):
        """测试创建响应"""
        response = TTSResponse(
            audio_data=b"audio_bytes",
            sample_rate=22050,
            duration=1.5,
        )
        assert response.audio_data == b"audio_bytes"
        assert response.sample_rate == 22050
        assert response.duration == 1.5

    def test_response_format(self):
        """测试响应格式"""
        response = TTSResponse(
            audio_data=b"data",
            sample_rate=16000,
            format="wav",
        )
        assert response.format == "wav"


class TestTTSAdapter:
    """TTS 适配器测试"""

    @pytest.fixture
    def config(self) -> TTSConfig:
        """创建测试配置"""
        return TTSConfig(
            mode="local",
            default_character="mika",
        )

    @pytest.fixture
    def cloud_config(self) -> TTSConfig:
        """创建云端配置"""
        return TTSConfig(
            mode="cloud",
            api_url="http://example.com/api/tts",
            api_key="test-key",
        )

    @pytest.fixture
    def mock_genie(self):
        """Mock Genie TTS"""
        with patch("src.tts.adapter.genie") as mock:
            mock.tts = MagicMock(return_value=b"audio_data")
            mock.load_predefined_character = MagicMock()
            yield mock

    @pytest.fixture
    def adapter(self, config: TTSConfig, mock_genie) -> TTSAdapter:
        """创建适配器"""
        return TTSAdapter(config)

    def test_init_local_mode(self, config: TTSConfig, mock_genie):
        """测试本地模式初始化"""
        adapter = TTSAdapter(config)
        assert adapter.mode == "local"
        assert adapter.config == config

    def test_init_cloud_mode(self, cloud_config: TTSConfig):
        """测试云端模式初始化"""
        adapter = TTSAdapter(cloud_config)
        assert adapter.mode == "cloud"
        assert adapter.api_url == "http://example.com/api/tts"

    @pytest.mark.asyncio
    async def test_synthesize_local(self, adapter: TTSAdapter, mock_genie):
        """测试本地合成"""
        request = TTSRequest(
            text="你好",
            character_name="mika",
        )

        response = await adapter.synthesize(request)

        assert response.audio_data is not None
        mock_genie.tts.assert_called()

    @pytest.mark.asyncio
    async def test_synthesize_with_default_character(self, adapter: TTSAdapter, mock_genie):
        """测试使用默认角色"""
        request = TTSRequest(text="测试")

        response = await adapter.synthesize(request)

        assert response.audio_data is not None

    @pytest.mark.asyncio
    async def test_synthesize_cloud(self, cloud_config: TTSConfig):
        """测试云端合成"""
        adapter = TTSAdapter(cloud_config)

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.content = b"cloud_audio"
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "audio/wav"}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            request = TTSRequest(text="云端测试")
            response = await adapter.synthesize(request)

            assert response.audio_data == b"cloud_audio"

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, adapter: TTSAdapter):
        """测试空文本"""
        request = TTSRequest(text="")

        with pytest.raises(ValueError, match="文本不能为空"):
            await adapter.synthesize(request)

    @pytest.mark.asyncio
    async def test_load_character(self, adapter: TTSAdapter, mock_genie):
        """测试加载角色"""
        await adapter.load_character("feibi")
        mock_genie.load_predefined_character.assert_called_with("feibi")

    def test_get_available_characters(self, adapter: TTSAdapter, mock_genie):
        """测试获取可用角色"""
        mock_genie.get_predefined_characters = MagicMock(return_value=["mika", "feibi"])

        characters = adapter.get_available_characters()

        assert "mika" in characters
        assert "feibi" in characters

    @pytest.mark.asyncio
    async def test_synthesize_stream(self, adapter: TTSAdapter, mock_genie):
        """测试流式合成"""
        mock_genie.tts_stream = MagicMock(return_value=iter([b"chunk1", b"chunk2", b"chunk3"]))

        request = TTSRequest(text="流式测试")
        chunks = []

        async for chunk in adapter.synthesize_stream(request):
            chunks.append(chunk)

        assert len(chunks) >= 1
