"""
WebSocket 消息处理器
处理 ASR 和 TTS 的 WebSocket 通信
"""

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from ..asr.base import ASREngine, ASRLanguage
from ..config import ServerConfig
from .manager import ConnectionManager

logger = logging.getLogger(__name__)


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


class WebSocketHandler:
    """
    WebSocket 消息处理器

    处理来自客户端的 WebSocket 消息，
    包括 ASR 音频流和 TTS 请求
    """

    def __init__(
        self,
        config: ServerConfig,
        connection_manager: ConnectionManager,
        asr_engine: ASREngine | None = None,
        tts_synthesize: Callable[..., Awaitable[bytes]] | None = None,
    ):
        self.config = config
        self.manager = connection_manager
        self.asr_engine = asr_engine
        self.tts_synthesize = tts_synthesize

        # ASR 会话管理
        self._asr_sessions: dict[str, ASRSession] = {}

        # 消息处理器映射
        self._handlers: dict[str, Callable] = {
            MessageType.PING: self._handle_ping,
            MessageType.ASR_START: self._handle_asr_start,
            MessageType.ASR_STOP: self._handle_asr_stop,
            MessageType.TTS_REQUEST: self._handle_tts_request,
            MessageType.CONVERSATION_START: self._handle_conversation_start,
            MessageType.CONVERSATION_END: self._handle_conversation_end,
        }

    async def handle_connection(
        self, websocket: WebSocket, connection_id: str | None = None
    ) -> None:
        """
        处理 WebSocket 连接的完整生命周期

        Args:
            websocket: WebSocket 连接
            connection_id: 可选的连接 ID
        """
        conn_id = await self.manager.connect(websocket, connection_id)

        try:
            # 发送连接成功消息
            await self.manager.send_json(
                conn_id,
                {
                    "type": "connected",
                    "connection_id": conn_id,
                    "config": {
                        "asr_enabled": self.asr_engine is not None,
                        "tts_enabled": self.tts_synthesize is not None,
                        "sample_rate": self.config.websocket.sample_rate,
                    },
                },
            )

            # 消息循环
            while True:
                message = await self._receive_message(websocket)
                if message is None:
                    break

                await self._process_message(conn_id, message)

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {conn_id}")
        except Exception as e:
            logger.error(f"Error handling connection {conn_id}: {e}")
            await self.manager.send_json(
                conn_id,
                {
                    "type": MessageType.ERROR,
                    "error": str(e),
                },
            )
        finally:
            # 清理 ASR 会话
            await self._cleanup_asr_session(conn_id)
            await self.manager.disconnect(conn_id)

    async def _receive_message(self, websocket: WebSocket) -> dict[str, Any] | None:
        """
        接收 WebSocket 消息

        支持 JSON 文本消息和二进制音频数据
        """
        try:
            message = await websocket.receive()

            if "text" in message:
                return json.loads(message["text"])
            elif "bytes" in message:
                # 二进制消息，用于音频数据
                return {
                    "type": MessageType.ASR_AUDIO,
                    "audio": message["bytes"],
                }

            return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return None

    async def _process_message(self, connection_id: str, message: dict[str, Any]) -> None:
        """处理接收到的消息"""
        msg_type = message.get("type", "")

        # 处理音频数据
        if msg_type == MessageType.ASR_AUDIO:
            await self._handle_asr_audio(connection_id, message.get("audio", b""))
            return

        # 查找并执行处理器
        handler = self._handlers.get(msg_type)
        if handler:
            await handler(connection_id, message)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            await self.manager.send_json(
                connection_id,
                {
                    "type": MessageType.ERROR,
                    "error": f"Unknown message type: {msg_type}",
                },
            )

    async def _handle_ping(self, connection_id: str, message: dict[str, Any]) -> None:
        """处理心跳消息"""
        await self.manager.send_json(
            connection_id,
            {
                "type": MessageType.PONG,
                "timestamp": message.get("timestamp"),
            },
        )

    async def _handle_asr_start(self, connection_id: str, message: dict[str, Any]) -> None:
        """
        开始 ASR 流式识别会话

        消息格式：
        {
            "type": "asr_start",
            "language": "zh",  // 可选，默认自动检测
            "sample_rate": 16000,  // 可选
        }
        """
        if self.asr_engine is None:
            await self.manager.send_json(
                connection_id,
                {
                    "type": MessageType.ERROR,
                    "error": "ASR not available",
                },
            )
            return

        # 创建 ASR 会话
        language = ASRLanguage(message.get("language", "auto"))
        sample_rate = message.get("sample_rate", self.config.websocket.sample_rate)

        session = ASRSession(
            connection_id=connection_id,
            language=language,
            sample_rate=sample_rate,
            audio_buffer=b"",
        )

        self._asr_sessions[connection_id] = session

        # 更新连接状态
        self.manager.update_connection(
            connection_id,
            is_streaming_asr=True,
            sample_rate=sample_rate,
        )

        await self.manager.send_json(
            connection_id,
            {
                "type": "asr_ready",
                "session_id": connection_id,
                "language": language.value,
                "sample_rate": sample_rate,
            },
        )

        logger.info(f"ASR session started: {connection_id}")

    async def _handle_asr_audio(self, connection_id: str, audio_data: bytes) -> None:
        """
        处理 ASR 音频数据

        音频数据格式：PCM 16-bit Little Endian
        """
        session = self._asr_sessions.get(connection_id)
        if not session or not session.is_active:
            return

        # 累积音频数据
        session.audio_buffer += audio_data

        # 检查是否有足够的数据进行识别
        # 每 0.5 秒处理一次（16kHz, 16-bit = 16000 samples/s * 2 bytes * 0.5s = 16000 bytes）
        chunk_size = session.sample_rate * 2 // 2  # 0.5 秒的数据

        if len(session.audio_buffer) >= chunk_size:
            # 提取音频块
            audio_chunk = session.audio_buffer[:chunk_size]
            session.audio_buffer = session.audio_buffer[chunk_size:]

            # 转换为 numpy 数组
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0

            try:
                # 执行流式识别
                if hasattr(self.asr_engine, "transcribe_chunk"):
                    result = await self.asr_engine.transcribe_chunk(
                        audio_array,
                        session.sample_rate,
                        session.language,
                    )
                else:
                    # 如果引擎不支持流式，使用完整转录
                    result = await self.asr_engine.transcribe(
                        audio_array,
                        session.sample_rate,
                        session.language,
                    )

                if result and result.text:
                    await self.manager.send_json(
                        connection_id,
                        {
                            "type": MessageType.ASR_PARTIAL
                            if not result.is_final
                            else MessageType.ASR_RESULT,
                            "text": result.text,
                            "is_final": result.is_final,
                            "confidence": result.confidence,
                            "language": result.language,
                        },
                    )

            except Exception as e:
                logger.error(f"ASR error: {e}")
                await self.manager.send_json(
                    connection_id,
                    {
                        "type": MessageType.ERROR,
                        "error": f"ASR processing error: {e!s}",
                    },
                )

    async def _handle_asr_stop(self, connection_id: str, message: dict[str, Any]) -> None:
        """
        停止 ASR 流式识别会话

        处理剩余的音频缓冲并返回最终结果
        """
        session = self._asr_sessions.get(connection_id)
        if not session:
            return

        session.is_active = False

        # 处理剩余的音频
        if session.audio_buffer and len(session.audio_buffer) > 0:
            audio_array = (
                np.frombuffer(session.audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
            )

            try:
                result = await self.asr_engine.transcribe(
                    audio_array,
                    session.sample_rate,
                    session.language,
                )

                if result and result.text:
                    await self.manager.send_json(
                        connection_id,
                        {
                            "type": MessageType.ASR_RESULT,
                            "text": result.text,
                            "is_final": True,
                            "confidence": result.confidence,
                            "language": result.language,
                        },
                    )

            except Exception as e:
                logger.error(f"Final ASR error: {e}")

        # 清理会话
        await self._cleanup_asr_session(connection_id)

        await self.manager.send_json(
            connection_id,
            {
                "type": "asr_stopped",
            },
        )

        logger.info(f"ASR session stopped: {connection_id}")

    async def _cleanup_asr_session(self, connection_id: str) -> None:
        """清理 ASR 会话"""
        session = self._asr_sessions.pop(connection_id, None)
        if session and session.task:
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass

        self.manager.update_connection(connection_id, is_streaming_asr=False)

    async def _handle_tts_request(self, connection_id: str, message: dict[str, Any]) -> None:
        """
        处理 TTS 请求

        消息格式：
        {
            "type": "tts_request",
            "text": "要合成的文本",
            "character": "mika",  // 角色名称
            "speed": 1.0,  // 语速
            "stream": true,  // 是否流式返回
        }
        """
        if self.tts_synthesize is None:
            await self.manager.send_json(
                connection_id,
                {
                    "type": MessageType.ERROR,
                    "error": "TTS not available",
                },
            )
            return

        text = message.get("text", "")
        if not text:
            await self.manager.send_json(
                connection_id,
                {
                    "type": MessageType.ERROR,
                    "error": "No text provided",
                },
            )
            return

        character = message.get("character", "mika")
        speed = message.get("speed", 1.0)
        stream = message.get("stream", True)
        request_id = message.get("request_id", connection_id)

        try:
            # 更新连接状态
            self.manager.update_connection(connection_id, is_streaming_tts=True)

            if stream:
                # 流式 TTS
                await self._stream_tts(connection_id, request_id, text, character, speed)
            else:
                # 非流式 TTS
                audio_data = await self.tts_synthesize(
                    text=text,
                    character=character,
                    speed=speed,
                )

                await self.manager.send_bytes(connection_id, audio_data)
                await self.manager.send_json(
                    connection_id,
                    {
                        "type": MessageType.TTS_COMPLETE,
                        "request_id": request_id,
                    },
                )

        except Exception as e:
            logger.error(f"TTS error: {e}")
            await self.manager.send_json(
                connection_id,
                {
                    "type": MessageType.ERROR,
                    "error": f"TTS error: {e!s}",
                    "request_id": request_id,
                },
            )
        finally:
            self.manager.update_connection(connection_id, is_streaming_tts=False)

    async def _stream_tts(
        self,
        connection_id: str,
        request_id: str,
        text: str,
        character: str,
        speed: float,
    ) -> None:
        """流式 TTS 合成和发送"""
        # 这里假设 tts_synthesize 支持流式返回
        # 如果不支持，需要分句处理

        # 简单分句
        sentences = self._split_sentences(text)

        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            try:
                audio_data = await self.tts_synthesize(
                    text=sentence,
                    character=character,
                    speed=speed,
                )

                # 发送音频数据
                await self.manager.send_json(
                    connection_id,
                    {
                        "type": MessageType.TTS_AUDIO,
                        "request_id": request_id,
                        "chunk_index": i,
                        "is_last": i == len(sentences) - 1,
                    },
                )
                await self.manager.send_bytes(connection_id, audio_data)

            except Exception as e:
                logger.error(f"TTS chunk error: {e}")
                raise

        await self.manager.send_json(
            connection_id,
            {
                "type": MessageType.TTS_COMPLETE,
                "request_id": request_id,
            },
        )

    def _split_sentences(self, text: str) -> list:
        """简单分句"""
        # 按中英文句号、问号、感叹号分割
        sentences = re.split(r"([。！？\.!?])", text)

        # 合并标点符号
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                result.append(sentence)

        # 处理最后一个片段
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1])

        return result if result else [text]

    async def _handle_conversation_start(self, connection_id: str, message: dict[str, Any]) -> None:
        """开始语音对话模式"""
        # 同时启动 ASR 和准备 TTS
        await self._handle_asr_start(connection_id, message)

        await self.manager.send_json(
            connection_id,
            {
                "type": "conversation_ready",
                "connection_id": connection_id,
            },
        )

    async def _handle_conversation_end(self, connection_id: str, message: dict[str, Any]) -> None:
        """结束语音对话模式"""
        await self._handle_asr_stop(connection_id, message)

        await self.manager.send_json(
            connection_id,
            {
                "type": "conversation_ended",
                "connection_id": connection_id,
            },
        )
