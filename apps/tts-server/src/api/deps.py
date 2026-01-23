"""API dependency helpers."""

from __future__ import annotations

from ..asr.factory import ASREngineFactory
from ..config import get_config
from ..tts.adapter import TTSAdapterFactory
from ..websocket.handler import WebSocketHandler
from ..websocket.manager import ConnectionManager

_connection_manager: ConnectionManager | None = None
_websocket_handler: WebSocketHandler | None = None


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器单例"""
    global _connection_manager
    if _connection_manager is None:
        config = get_config()
        _connection_manager = ConnectionManager(max_connections=config.websocket.max_connections)
    return _connection_manager


def get_websocket_handler() -> WebSocketHandler:
    """获取 WebSocket 处理器单例"""
    global _websocket_handler
    if _websocket_handler is None:
        config = get_config()
        _websocket_handler = WebSocketHandler(config, get_connection_manager())
    return _websocket_handler


async def get_tts_adapter():
    """获取 TTS 适配器"""
    config = get_config()
    return TTSAdapterFactory.create(config)


async def get_asr_engine():
    """获取 ASR 引擎"""
    config = get_config()
    return ASREngineFactory.create(config)
