"""TTS 适配器测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import InferenceMode, TTSConfig, TTSProvider
from src.tts.base import TTSResult
from src.tts.cloud_adapter import CloudTTSAdapter
from src.tts.factory import TTSAdapterFactory
from src.tts.genie_adapter import GenieTTSAdapter


class TestTTSResult:
    """TTS 结果测试"""

    def test_create_result(self):
        result = TTSResult(audio=b"audio", sample_rate=22050, format="wav", duration=1.5)
        assert result.audio == b"audio"
        assert result.sample_rate == 22050
        assert result.format == "wav"
        assert result.duration == 1.5


class TestTTSAdapterFactory:
    """TTS 适配器工厂测试"""

    def test_create_genie_adapter(self):
        config = TTSConfig(mode=InferenceMode.LOCAL, provider=TTSProvider.GENIE_TTS)
        adapter = TTSAdapterFactory.create(config)
        assert isinstance(adapter, GenieTTSAdapter)

    def test_create_cloud_adapter(self):
        config = TTSConfig(mode=InferenceMode.CLOUD, provider=TTSProvider.CLOUD_API)
        adapter = TTSAdapterFactory.create(config)
        assert isinstance(adapter, CloudTTSAdapter)


class TestGenieTTSAdapter:
    """Genie TTS 适配器测试"""

    def test_list_characters_defaults(self):
        adapter = GenieTTSAdapter(characters=["mika", "feibi"])
        characters = adapter.list_characters()
        assert "mika" in characters
        assert "feibi" in characters


class TestCloudTTSAdapter:
    """Cloud TTS 适配器测试"""

    @pytest.mark.asyncio
    async def test_synthesize_custom_audio(self):
        adapter = CloudTTSAdapter(provider="custom", api_key="key", api_url="https://api.example.com")

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "audio/wav"}
        mock_response.content = b"cloud_audio"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await adapter.synthesize(text="hello", character="default", speed=1.0)

        assert result.audio == b"cloud_audio"
