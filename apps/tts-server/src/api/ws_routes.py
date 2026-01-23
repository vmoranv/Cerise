"""WebSocket routes for the TTS server API."""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .deps import get_websocket_handler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点

    支持实时 ASR 和 TTS 交互

    消息格式：
    - 文本消息：JSON 格式的控制消息
    - 二进制消息：音频数据

    控制消息类型：
    - ping/pong：心跳
    - asr_start：开始 ASR 会话
    - asr_stop：停止 ASR 会话
    - tts_request：TTS 合成请求
    - conversation_start/end：会话管理
    """
    handler = get_websocket_handler()
    connection_id = None

    try:
        connection_id = await handler.handle_connect(websocket)

        while True:
            try:
                # 尝试接收消息（支持文本和二进制）
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    if "text" in message:
                        # 文本消息（JSON）
                        await handler.handle_text_message(connection_id, message["text"])
                    elif "bytes" in message:
                        # 二进制消息（音频数据）
                        await handler.handle_binary_message(connection_id, message["bytes"])
                elif message["type"] == "websocket.disconnect":
                    break

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
    finally:
        if connection_id:
            await handler.handle_disconnect(connection_id)


@router.websocket("/ws/asr")
async def websocket_asr_endpoint(websocket: WebSocket):
    """
    专用 ASR WebSocket 端点

    简化的 ASR 流式识别接口：
    1. 连接建立后直接开始 ASR 会话
    2. 发送二进制音频数据
    3. 接收 JSON 格式的识别结果
    """
    handler = get_websocket_handler()
    connection_id = None

    try:
        connection_id = await handler.handle_connect(websocket)

        # 自动开始 ASR 会话
        await handler.handle_text_message(connection_id, '{"type": "asr_start", "language": null}')

        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # 处理音频数据
                        await handler.handle_binary_message(connection_id, message["bytes"])
                    elif "text" in message:
                        # 处理控制消息
                        await handler.handle_text_message(connection_id, message["text"])
                elif message["type"] == "websocket.disconnect":
                    break

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"ASR WebSocket 错误: {e}")
    finally:
        if connection_id:
            # 停止 ASR 会话
            with contextlib.suppress(Exception):
                await handler.handle_text_message(connection_id, '{"type": "asr_stop"}')
            await handler.handle_disconnect(connection_id)


@router.websocket("/ws/tts")
async def websocket_tts_endpoint(websocket: WebSocket):
    """
    专用 TTS WebSocket 端点

    简化的 TTS 流式合成接口：
    1. 发送 JSON 格式的合成请求
    2. 接收二进制音频数据流
    """
    handler = get_websocket_handler()
    connection_id = None

    try:
        connection_id = await handler.handle_connect(websocket)

        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.receive":
                    if "text" in message:
                        # 处理 TTS 请求
                        await handler.handle_text_message(connection_id, message["text"])
                elif message["type"] == "websocket.disconnect":
                    break

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"TTS WebSocket 错误: {e}")
    finally:
        if connection_id:
            await handler.handle_disconnect(connection_id)
