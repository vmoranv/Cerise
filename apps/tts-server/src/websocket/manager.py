"""
WebSocket 连接管理器
管理所有活跃的 WebSocket 连接
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .manager_health import ConnectionManagerHealthMixin
from .types import ConnectionInfo, ConnectionState

logger = logging.getLogger(__name__)


class ConnectionManager(ConnectionManagerHealthMixin):
    """
    WebSocket 连接管理器

    功能：
    - 管理所有活跃连接
    - 提供广播和单播消息功能
    - 处理连接生命周期
    - 连接分组管理
    """

    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self._connections: dict[str, ConnectionInfo] = {}
        self._groups: dict[str, set[str]] = {}  # group_name -> connection_ids
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)

    @property
    def connections(self) -> dict[str, ConnectionInfo]:
        """所有连接"""
        return self._connections.copy()

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        接受新连接

        Args:
            websocket: WebSocket 实例
            connection_id: 可选的连接 ID，不提供则自动生成
            metadata: 连接元数据

        Returns:
            连接 ID

        Raises:
            ConnectionError: 超过最大连接数
        """
        async with self._lock:
            if len(self._connections) >= self.max_connections:
                await websocket.close(code=1013, reason="Server overloaded")
                raise ConnectionError("Maximum connections reached")

            conn_id = connection_id or str(uuid.uuid4())

            await websocket.accept()

            self._connections[conn_id] = ConnectionInfo(
                id=conn_id,
                websocket=websocket,
                state=ConnectionState.CONNECTED,
                metadata=metadata or {},
            )

            logger.info(f"WebSocket connected: {conn_id}")
            return conn_id

    async def disconnect(
        self, connection_id: str, code: int = 1000, reason: str = "Normal closure"
    ) -> None:
        """
        断开连接

        Args:
            connection_id: 连接 ID
            code: 关闭代码
            reason: 关闭原因
        """
        async with self._lock:
            if connection_id not in self._connections:
                return

            conn_info = self._connections[connection_id]
            conn_info.state = ConnectionState.DISCONNECTING

            try:
                await conn_info.websocket.close(code=code, reason=reason)
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")

            # 从所有分组中移除
            for group_connections in self._groups.values():
                group_connections.discard(connection_id)

            del self._connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")

    def get_connection(self, connection_id: str) -> ConnectionInfo | None:
        """获取连接信息"""
        return self._connections.get(connection_id)

    def update_connection(self, connection_id: str, **kwargs) -> None:
        """更新连接信息"""
        if connection_id in self._connections:
            conn = self._connections[connection_id]
            for key, value in kwargs.items():
                if hasattr(conn, key):
                    setattr(conn, key, value)
            conn.last_active = datetime.now()

    async def send_json(self, connection_id: str, data: dict) -> bool:
        """
        发送 JSON 数据到指定连接

        Returns:
            是否发送成功
        """
        conn_info = self._connections.get(connection_id)
        if not conn_info:
            return False

        try:
            await conn_info.websocket.send_json(data)
            conn_info.last_active = datetime.now()
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            return False

    async def send_bytes(self, connection_id: str, data: bytes) -> bool:
        """
        发送二进制数据到指定连接

        Returns:
            是否发送成功
        """
        conn_info = self._connections.get(connection_id)
        if not conn_info:
            return False

        try:
            await conn_info.websocket.send_bytes(data)
            conn_info.last_active = datetime.now()
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending bytes to {connection_id}: {e}")
            return False

    async def send_text(self, connection_id: str, text: str) -> bool:
        """发送文本消息"""
        conn_info = self._connections.get(connection_id)
        if not conn_info:
            return False

        try:
            await conn_info.websocket.send_text(text)
            conn_info.last_active = datetime.now()
            return True
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
            return False
        except Exception as e:
            logger.error(f"Error sending text to {connection_id}: {e}")
            return False

    async def broadcast_json(
        self,
        data: dict,
        exclude: set[str] | None = None,
        group: str | None = None,
    ) -> int:
        """
        广播 JSON 数据

        Args:
            data: 要发送的数据
            exclude: 要排除的连接 ID
            group: 只发送给指定分组

        Returns:
            成功发送的连接数
        """
        exclude = exclude or set()

        if group:
            target_ids = self._groups.get(group, set()) - exclude
        else:
            target_ids = set(self._connections.keys()) - exclude

        success_count = 0
        tasks = [self.send_json(conn_id, data) for conn_id in target_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result is True:
                success_count += 1

        return success_count

    async def broadcast_bytes(
        self,
        data: bytes,
        exclude: set[str] | None = None,
        group: str | None = None,
    ) -> int:
        """广播二进制数据"""
        exclude = exclude or set()

        if group:
            target_ids = self._groups.get(group, set()) - exclude
        else:
            target_ids = set(self._connections.keys()) - exclude

        success_count = 0
        tasks = [self.send_bytes(conn_id, data) for conn_id in target_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if result is True:
                success_count += 1

        return success_count

    # 分组管理
    def add_to_group(self, connection_id: str, group: str) -> None:
        """将连接添加到分组"""
        if connection_id not in self._connections:
            return

        if group not in self._groups:
            self._groups[group] = set()

        self._groups[group].add(connection_id)

    def remove_from_group(self, connection_id: str, group: str) -> None:
        """将连接从分组移除"""
        if group in self._groups:
            self._groups[group].discard(connection_id)

    def get_group_members(self, group: str) -> set[str]:
        """获取分组成员"""
        return self._groups.get(group, set()).copy()
