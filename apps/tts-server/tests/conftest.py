"""
Pytest 配置和 fixtures
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.config import (
    ASRConfig,
    Config,
    ServerConfig,
    TTSConfig,
    WebSocketConfig,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环用于异步测试"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config() -> Config:
    """创建示例配置"""
    return Config(
        server=ServerConfig(
            host="127.0.0.1",
            port=8000,
            workers=1,
            debug=True,
        ),
        asr=ASRConfig(
            engine="funasr",
            model="paraformer-zh",
            language="auto",
            device="cpu",
            enable_punctuation=True,
            enable_itn=True,
        ),
        tts=TTSConfig(
            mode="local",
            default_character="mika",
            sample_rate=24000,
            cloud_provider=None,
            cloud_api_key=None,
            cloud_api_url=None,
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
    # 生成 1 秒的静音音频（全零）
    sample_rate = 16000
    duration = 1  # 秒
    num_samples = sample_rate * duration
    # 16-bit PCM: 每个样本 2 字节
    return bytes(num_samples * 2)


@pytest.fixture
def sample_audio_data_with_noise() -> bytes:
    """创建带噪声的示例音频数据"""
    import random

    sample_rate = 16000
    duration = 1
    num_samples = sample_rate * duration
    # 生成随机噪声
    return bytes(random.randint(0, 255) for _ in range(num_samples * 2))


@pytest.fixture
def mock_genie_tts() -> Generator[MagicMock, None, None]:
    """Mock genie_tts 模块"""
    with patch("src.tts.adapter.genie") as mock:
        mock.load_predefined_character = MagicMock()
        mock.tts = MagicMock(return_value=b"mock_audio_data")
        mock.wait_for_playback_done = MagicMock()
        yield mock


@pytest.fixture
def mock_funasr() -> Generator[MagicMock, None, None]:
    """Mock FunASR 模块"""
    with patch("src.asr.funasr_engine.AutoModel") as mock:
        mock_instance = MagicMock()
        mock_instance.generate = MagicMock(
            return_value=[{"text": "测试文本", "timestamp": [[0, 100, 1000]]}]
        )
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_whisper() -> Generator[MagicMock, None, None]:
    """Mock faster-whisper 模块"""
    with patch("src.asr.whisper_engine.WhisperModel") as mock:
        mock_instance = MagicMock()
        # 模拟转录结果
        mock_segment = MagicMock()
        mock_segment.text = "测试文本"
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.no_speech_prob = 0.1

        mock_info = MagicMock()
        mock_info.language = "zh"
        mock_info.language_probability = 0.95

        mock_instance.transcribe = MagicMock(return_value=([mock_segment], mock_info))
        mock.return_value = mock_instance
        yield mock


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
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def temp_config_file(tmp_path: str) -> str:
    """创建临时配置文件"""
    config_content = """
server:
  host: "127.0.0.1"
  port: 8080
  workers: 2
  debug: true

asr:
  engine: "whisper"
  model: "small"
  language: "zh"
  device: "cpu"
  enable_punctuation: true
  enable_itn: false

tts:
  mode: "local"
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
