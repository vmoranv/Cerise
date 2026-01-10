"""
WebSocket 模块
处理实时语音通信
"""

from .handler import WebSocketHandler
from .manager import ConnectionManager

__all__ = [
    "WebSocketHandler",
    "ConnectionManager",
]
