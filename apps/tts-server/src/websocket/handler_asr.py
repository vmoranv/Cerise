"""ASR handling helpers for WebSocket handler."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np

from ..asr.base import ASREngine, ASRLanguage
from ..config import ServerConfig
from .manager import ConnectionManager
from .types import ASRSession, MessageType

logger = logging.getLogger(__name__)


class ASRHandlerMixin:
    asr_engine: ASREngine | None
    config: ServerConfig
    manager: ConnectionManager
    _asr_sessions: dict[str, ASRSession]

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
