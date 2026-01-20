"""
配置管理模块
支持本地推理和云端 API 两种模式
"""

import os
from enum import Enum

import yaml
from pydantic import BaseModel, Field


class InferenceMode(str, Enum):
    """推理模式枚举"""

    LOCAL = "local"  # 本地推理
    CLOUD = "cloud"  # 云端 API


class ASRProvider(str, Enum):
    """ASR 提供者枚举"""

    FUNASR = "funasr"  # 阿里达摩院 FunASR（推荐，中日英支持好）
    WHISPER = "whisper"  # OpenAI Whisper / faster-whisper
    CLOUD_API = "cloud_api"  # 云端 ASR API


class TTSProvider(str, Enum):
    """TTS 提供者枚举"""

    GENIE_TTS = "genie_tts"  # 本地 Genie-TTS (GPT-SoVITS)
    CLOUD_API = "cloud_api"  # 云端 TTS API


class ASRConfig(BaseModel):
    """ASR 配置"""

    provider: ASRProvider = ASRProvider.FUNASR
    mode: InferenceMode = InferenceMode.LOCAL

    # FunASR 本地配置
    funasr_model: str = (
        "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    )
    funasr_vad_model: str = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    funasr_punc_model: str = "iic/punc_ct-transformer_cn-en-common-vocab471067-large"
    funasr_device: str = "cuda"  # cuda / cpu

    # Whisper 本地配置
    whisper_model: str = "large-v3"  # tiny, base, small, medium, large-v3
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"  # float16, int8

    # 云端 API 配置
    cloud_api_url: str | None = None
    cloud_api_key: str | None = None
    cloud_api_model: str | None = None


class TTSConfig(BaseModel):
    """TTS 配置"""

    provider: TTSProvider = TTSProvider.GENIE_TTS
    mode: InferenceMode = InferenceMode.LOCAL

    # Genie-TTS 本地配置
    default_character: str = "mika"
    split_sentence: bool = True

    # 云端 API 配置
    cloud_api_url: str | None = None
    cloud_api_key: str | None = None
    cloud_voice_id: str | None = None


class WebSocketConfig(BaseModel):
    """WebSocket 配置"""

    # 音频流配置
    sample_rate: int = 16000  # 采样率
    channels: int = 1  # 通道数
    chunk_duration_ms: int = 100  # 每个音频块的时长（毫秒）

    # VAD 配置
    enable_vad: bool = True  # 启用语音活动检测
    vad_threshold: float = 0.5  # VAD 阈值
    silence_duration_ms: int = 500  # 静音判定时长（毫秒）

    # 连接配置
    ping_interval: int = 30  # ping 间隔（秒）
    ping_timeout: int = 10  # ping 超时（秒）
    max_message_size: int = 10485760  # 最大消息大小（10MB）


class ServerConfig(BaseModel):
    """服务器总配置"""

    host: str = "0.0.0.0"
    port: int = 8001
    workers: int = 1

    # 子配置
    asr: ASRConfig = Field(default_factory=ASRConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)

    # 日志配置
    log_level: str = "INFO"

    class Config:
        env_prefix = "VOICE_SERVER_"


def load_config(config_path: str | None = None) -> ServerConfig:
    """
    加载配置
    优先级：配置文件 > 环境变量 > 默认值
    """
    config = ServerConfig()

    # 从配置文件加载
    if config_path and os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            file_config = yaml.safe_load(f)
            if file_config:
                config = ServerConfig(**file_config)

    # 环境变量覆盖
    if os.getenv("VOICE_SERVER_ASR_MODE"):
        config.asr.mode = InferenceMode(os.getenv("VOICE_SERVER_ASR_MODE"))
    if os.getenv("VOICE_SERVER_TTS_MODE"):
        config.tts.mode = InferenceMode(os.getenv("VOICE_SERVER_TTS_MODE"))
    if os.getenv("VOICE_SERVER_ASR_CLOUD_API_URL"):
        config.asr.cloud_api_url = os.getenv("VOICE_SERVER_ASR_CLOUD_API_URL")
    if os.getenv("VOICE_SERVER_ASR_CLOUD_API_KEY"):
        config.asr.cloud_api_key = os.getenv("VOICE_SERVER_ASR_CLOUD_API_KEY")
    if os.getenv("VOICE_SERVER_TTS_CLOUD_API_URL"):
        config.tts.cloud_api_url = os.getenv("VOICE_SERVER_TTS_CLOUD_API_URL")
    if os.getenv("VOICE_SERVER_TTS_CLOUD_API_KEY"):
        config.tts.cloud_api_key = os.getenv("VOICE_SERVER_TTS_CLOUD_API_KEY")

    return config


# 全局配置实例
_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: ServerConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config
