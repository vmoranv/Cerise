"""
配置模块测试
"""

from pathlib import Path
from unittest.mock import patch

from src.config import (
    ASRConfig,
    Config,
    ServerConfig,
    TTSConfig,
    WebSocketConfig,
    load_config,
)


class TestServerConfig:
    """服务器配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 1
        assert config.debug is False

    def test_custom_values(self):
        """测试自定义值"""
        config = ServerConfig(
            host="127.0.0.1",
            port=9000,
            workers=4,
            debug=True,
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.workers == 4
        assert config.debug is True


class TestASRConfig:
    """ASR 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = ASRConfig()
        assert config.engine == "funasr"
        assert config.model == "paraformer-zh"
        assert config.language == "auto"
        assert config.device == "cuda"
        assert config.enable_punctuation is True
        assert config.enable_itn is True

    def test_whisper_engine(self):
        """测试 Whisper 引擎配置"""
        config = ASRConfig(
            engine="whisper",
            model="small",
            language="zh",
            device="cpu",
        )
        assert config.engine == "whisper"
        assert config.model == "small"
        assert config.language == "zh"
        assert config.device == "cpu"


class TestTTSConfig:
    """TTS 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = TTSConfig()
        assert config.mode == "local"
        assert config.default_character == "mika"
        assert config.sample_rate == 24000
        assert config.cloud_provider is None

    def test_cloud_mode(self):
        """测试云端模式配置"""
        config = TTSConfig(
            mode="cloud",
            cloud_provider="azure",
            cloud_api_key="test-key",
            cloud_api_url="https://api.example.com",
        )
        assert config.mode == "cloud"
        assert config.cloud_provider == "azure"
        assert config.cloud_api_key == "test-key"


class TestWebSocketConfig:
    """WebSocket 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = WebSocketConfig()
        assert config.max_connections == 100
        assert config.heartbeat_interval == 30
        assert config.max_message_size == 10485760  # 10MB

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


class TestConfig:
    """主配置类测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.asr, ASRConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.websocket, WebSocketConfig)

    def test_nested_config(self, sample_config: Config):
        """测试嵌套配置"""
        assert sample_config.server.host == "127.0.0.1"
        assert sample_config.asr.engine == "funasr"
        assert sample_config.tts.mode == "local"
        assert sample_config.websocket.max_connections == 100


class TestLoadConfig:
    """配置加载测试"""

    def test_load_config_from_file(self, temp_config_file: str):
        """测试从文件加载配置"""
        config = load_config(temp_config_file)
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8080
        assert config.asr.engine == "whisper"
        assert config.tts.default_character == "feibi"

    def test_load_config_default(self):
        """测试默认配置加载"""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_config()
            assert isinstance(config, Config)
            assert config.server.host == "0.0.0.0"

    def test_load_config_file_not_found(self):
        """测试文件不存在时返回默认配置"""
        config = load_config("nonexistent_config.yaml")
        assert isinstance(config, Config)

    def test_load_config_invalid_yaml(self, tmp_path: Path):
        """测试无效 YAML 格式"""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        # 应该返回默认配置而不是抛出异常
        config = load_config(str(config_file))
        assert isinstance(config, Config)

    def test_load_config_partial(self, tmp_path: Path):
        """测试部分配置"""
        config_content = """
server:
  port: 9999
"""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))
        assert config.server.port == 9999
        # 其他值应该是默认值
        assert config.server.host == "0.0.0.0"
        assert config.asr.engine == "funasr"
