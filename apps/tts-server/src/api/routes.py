"""API route aggregation.

整合 HTTP REST API 和 WebSocket 端点
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, WebSocket

from .http_routes import health_check, router as http_router
from .ws_routes import (
    router as ws_router,
    websocket_asr_endpoint,
    websocket_endpoint,
    websocket_tts_endpoint,
)

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(http_router)
router.include_router(ws_router)


def setup_routes(app: FastAPI, prefix: str = "/api/v1"):
    """
    设置 API 路由

    Args:
        app: FastAPI 应用实例
        prefix: API 路径前缀
    """
    # 添加带前缀的路由
    app.include_router(router, prefix=prefix)

    # 添加根级别的 WebSocket 端点（不带前缀）
    @app.websocket("/ws")
    async def root_websocket(websocket: WebSocket):
        await websocket_endpoint(websocket)

    @app.websocket("/ws/asr")
    async def root_asr_websocket(websocket: WebSocket):
        await websocket_asr_endpoint(websocket)

    @app.websocket("/ws/tts")
    async def root_tts_websocket(websocket: WebSocket):
        await websocket_tts_endpoint(websocket)

    # 添加根级别的健康检查
    @app.get("/health")
    async def root_health():
        return await health_check()

    logger.info(f"API 路由已设置，前缀: {prefix}")
