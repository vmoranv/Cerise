"""TTS handling helpers for WebSocket handler."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .manager import ConnectionManager
from .types import MessageType

logger = logging.getLogger(__name__)


class TTSHandlerMixin:
    tts_synthesize: Callable[..., Awaitable[bytes]] | None
    manager: ConnectionManager

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
