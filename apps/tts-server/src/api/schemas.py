"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """TTS 合成请求"""

    text: str = Field(..., description="要合成的文本")
    character: str = Field(default="mika", description="角色名称")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    format: str = Field(default="wav", description="输出格式: wav, mp3, ogg")
    stream: bool = Field(default=False, description="是否流式返回")


class TTSResponse(BaseModel):
    """TTS 合成响应（非流式）"""

    success: bool
    audio_base64: str | None = None
    sample_rate: int = 24000
    duration: float | None = None
    error: str | None = None


class ASRRequest(BaseModel):
    """ASR 识别请求（用于 base64 音频）"""

    audio_base64: str = Field(..., description="Base64 编码的音频数据")
    sample_rate: int = Field(default=16000, description="音频采样率")
    language: str | None = Field(default=None, description="语言代码")
    format: str = Field(default="wav", description="音频格式")


class ASRResponse(BaseModel):
    """ASR 识别响应"""

    success: bool
    text: str | None = None
    language: str | None = None
    confidence: float | None = None
    duration: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    inference_mode: str
    asr_provider: str
    tts_provider: str
    asr_ready: bool
    tts_ready: bool
    websocket_connections: int


class ConfigResponse(BaseModel):
    """配置信息响应"""

    inference_mode: str
    asr: dict
    tts: dict
    websocket: dict
    available_characters: list
