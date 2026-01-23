"""WebSocket 消息处理器
处理 ASR 和 TTS 的 WebSocket 通信
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..asr.base import ASREngine
from ..config import ServerConfig
from .handler_asr import ASRHandlerMixin
from .handler_tts import TTSHandlerMixin
from .manager import ConnectionManager
from .types import ASRSession, MessageType

logger = logging.getLogger(__name__)


class WebSocketHandler(ASRHandlerMixin, TTSHandlerMixin):
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
