"""WebSocket message types and session models."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum

from ..asr.base import ASRLanguage


class MessageType(str, Enum):
    """WebSocket 消息类型"""

    # 控制消息
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # ASR 消息
    ASR_START = "asr_start"
    ASR_AUDIO = "asr_audio"
    ASR_STOP = "asr_stop"
    ASR_RESULT = "asr_result"
    ASR_PARTIAL = "asr_partial"

    # TTS 消息
    TTS_REQUEST = "tts_request"
    TTS_AUDIO = "tts_audio"
    TTS_COMPLETE = "tts_complete"

    # 语音对话消息
    CONVERSATION_START = "conversation_start"
    CONVERSATION_END = "conversation_end"


@dataclass
class ASRSession:
    """ASR 流式会话"""

    connection_id: str
    language: ASRLanguage
    sample_rate: int
    audio_buffer: bytes
    is_active: bool = True
    task: asyncio.Task | None = None
