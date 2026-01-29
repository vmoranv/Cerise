"""WebSocket message types and session models."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket

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


class ConnectionState(str, Enum):
    """Connection state."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class ConnectionInfo:
    """Connection metadata."""

    id: str
    websocket: WebSocket
    state: ConnectionState = ConnectionState.CONNECTING
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    is_streaming_asr: bool = False
    is_streaming_tts: bool = False

    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "pcm"


@dataclass
class ASRSession:
    """ASR 流式会话"""

    connection_id: str
    language: ASRLanguage
    sample_rate: int
    audio_buffer: bytes
    is_active: bool = True
    task: asyncio.Task | None = None
