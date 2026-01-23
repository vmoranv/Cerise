"""Pytest fixtures for tts-server tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.config import (
    ASRConfig,
    ASRProvider,
    InferenceMode,
    ServerConfig,
    TTSConfig,
    TTSProvider,
    WebSocketConfig,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环用于异步测试"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config() -> ServerConfig:
    """创建示例配置"""
    return ServerConfig(
        host="127.0.0.1",
        port=8000,
        workers=1,
        asr=ASRConfig(
            provider=ASRProvider.WHISPER,
            mode=InferenceMode.LOCAL,
            language="zh",
            whisper_model="base",
            whisper_device="cpu",
        ),
        tts=TTSConfig(
            provider=TTSProvider.GENIE_TTS,
            mode=InferenceMode.LOCAL,
            default_character="mika",
            sample_rate=24000,
        ),
        websocket=WebSocketConfig(
            max_connections=100,
            heartbeat_interval=30,
            max_message_size=10485760,
        ),
    )


@pytest.fixture
def sample_audio_data() -> bytes:
    """创建示例音频数据（模拟 16-bit PCM, 16kHz）"""
    sample_rate = 16000
    duration = 1
    num_samples = sample_rate * duration
    return bytes(num_samples * 2)


@pytest.fixture
def sample_audio_data_with_noise() -> bytes:
    """创建带噪声的示例音频数据"""
    import random

    sample_rate = 16000
    duration = 1
    num_samples = sample_rate * duration
    return bytes(random.randint(0, 255) for _ in range(num_samples * 2))


@pytest_asyncio.fixture
async def mock_websocket() -> AsyncGenerator[AsyncMock, None]:
    """Mock WebSocket 连接"""
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.send_bytes = AsyncMock()
    mock_ws.receive = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.client_state = MagicMock()
    mock_ws.client_state.CONNECTED = True
    yield mock_ws


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Mock httpx 异步客户端"""
    with patch("httpx.AsyncClient") as mock:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "text": "云端识别结果",
                "confidence": 0.95,
            }
        )
        mock_response.status_code = 200
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def temp_config_file(tmp_path: Path) -> str:
    """创建临时配置文件"""
    config_content = """
host: "127.0.0.1"
port: 8080
workers: 2

asr:
  provider: whisper
  mode: local
  language: "zh"
  whisper_model: "small"
  whisper_device: "cpu"

tts:
  provider: genie_tts
  mode: local
  default_character: "feibi"
  sample_rate: 22050

websocket:
  max_connections: 50
  heartbeat_interval: 20
  max_message_size: 5242880
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)

