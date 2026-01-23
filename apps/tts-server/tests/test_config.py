"""配置模块测试"""

from pathlib import Path
from unittest.mock import patch

from src.config import (
    ASRConfig,
    ASRProvider,
    InferenceMode,
    ServerConfig,
    TTSConfig,
    TTSProvider,
    WebSocketConfig,
    load_config,
)


class TestServerConfig:
    """服务器配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8001
        assert config.workers == 1
        assert config.log_level == "INFO"
        assert isinstance(config.asr, ASRConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.websocket, WebSocketConfig)

    def test_custom_values(self):
        """测试自定义值"""
        config = ServerConfig(
            host="127.0.0.1",
            port=9000,
            workers=4,
            log_level="DEBUG",
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.workers == 4
        assert config.log_level == "DEBUG"


class TestASRConfig:
    """ASR 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ASRConfig()
        assert config.provider == ASRProvider.FUNASR
        assert config.mode == InferenceMode.LOCAL
        assert config.language == "auto"
        assert config.funasr_device == "cuda"

    def test_whisper_engine(self):
        """测试 Whisper 引擎配置"""
        config = ASRConfig(
            provider=ASRProvider.WHISPER,
            whisper_model="small",
            whisper_device="cpu",
            language="zh",
        )
        assert config.provider == ASRProvider.WHISPER
        assert config.whisper_model == "small"
        assert config.whisper_device == "cpu"
        assert config.language == "zh"

    def test_get_model_name(self):
        """测试模型名选择"""
        config = ASRConfig(provider=ASRProvider.FUNASR)
        assert config.get_model_name() == config.funasr_model
        config = ASRConfig(provider=ASRProvider.WHISPER)
        assert config.get_model_name() == config.whisper_model


class TestTTSConfig:
    """TTS 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = TTSConfig()
        assert config.mode == InferenceMode.LOCAL
        assert config.provider == TTSProvider.GENIE_TTS
        assert config.default_character == "mika"
        assert config.sample_rate == 32000
        assert config.cloud_provider is None

    def test_cloud_mode(self):
        """测试云端模式配置"""
        config = TTSConfig(
            mode=InferenceMode.CLOUD,
            provider=TTSProvider.CLOUD_API,
            cloud_provider="azure",
            cloud_api_key="test-key",
            cloud_api_url="https://api.example.com",
        )
        assert config.mode == InferenceMode.CLOUD
        assert config.provider == TTSProvider.CLOUD_API
        assert config.cloud_provider == "azure"
        assert config.cloud_api_key == "test-key"


class TestWebSocketConfig:
    """WebSocket 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = WebSocketConfig()
        assert config.sample_rate == 16000
        assert config.max_connections == 100
        assert config.heartbeat_interval == 30
        assert config.max_message_size == 10485760

    def test_custom_values(self):
        """测试自定义值"""
        config = WebSocketConfig(
            max_connections=50,
            heartbeat_interval=15,
            max_message_size=5242880,
        )
        assert config.max_connections == 50
        assert config.heartbeat_interval == 15
        assert config.max_message_size == 5242880


class TestLoadConfig:
    """配置加载测试"""

    def test_load_config_from_file(self, temp_config_file: str):
        """测试从文件加载配置"""
        config = load_config(temp_config_file)
        assert isinstance(config, ServerConfig)
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.asr.provider == ASRProvider.WHISPER
        assert config.tts.default_character == "feibi"

    def test_load_config_default(self):
        """测试默认配置加载"""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_config()
            assert isinstance(config, ServerConfig)
            assert config.host == "0.0.0.0"

    def test_load_config_file_not_found(self):
        """测试文件不存在时返回默认配置"""
        config = load_config("nonexistent_config.yaml")
        assert isinstance(config, ServerConfig)

    def test_load_config_invalid_yaml(self, tmp_path: Path):
        """测试无效 YAML 格式"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config = load_config(str(config_file))
        assert isinstance(config, ServerConfig)

    def test_load_config_partial(self, tmp_path: Path):
        """测试部分配置"""
        config_content = """
port: 9999
"""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))
        assert config.port == 9999
        assert config.host == "0.0.0.0"
