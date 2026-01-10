"""
API 路由定义

整合 HTTP REST API 和 WebSocket 端点
"""

import base64
import contextlib
import logging
import time
from typing import Annotated

from fastapi import (
    APIRouter,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from ..asr.factory import ASREngineFactory
from ..config import get_config
from ..tts.adapter import TTSAdapterFactory
from ..websocket.handler import WebSocketHandler
from ..websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局实例
_connection_manager: ConnectionManager | None = None
_websocket_handler: WebSocketHandler | None = None


# ============ 请求/响应模型 ============


class TTSRequest(BaseModel):
    """TTS 合成请求"""

    text: str = Field(..., description="要合成的文本")
    character: str = Field(default="mika", description="角色名称")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    format: str = Field(default="wav", description="输出格式: wav, mp3, ogg")
    stream: bool = Field(default=False, description="是否流式返回")


class TTSResponse(BaseModel):
    """TTS 合成响应（非流式）"""

    success: bool
    audio_base64: str | None = None
    sample_rate: int = 24000
    duration: float | None = None
    error: str | None = None


class ASRRequest(BaseModel):
    """ASR 识别请求（用于 base64 音频）"""

    audio_base64: str = Field(..., description="Base64 编码的音频数据")
    sample_rate: int = Field(default=16000, description="音频采样率")
    language: str | None = Field(default=None, description="语言代码")
    format: str = Field(default="wav", description="音频格式")


class ASRResponse(BaseModel):
    """ASR 识别响应"""

    success: bool
    text: str | None = None
    language: str | None = None
    confidence: float | None = None
    duration: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    inference_mode: str
    asr_provider: str
    tts_provider: str
    asr_ready: bool
    tts_ready: bool
    websocket_connections: int


class ConfigResponse(BaseModel):
    """配置信息响应"""

    inference_mode: str
    asr: dict
    tts: dict
    websocket: dict
    available_characters: list


# ============ 辅助函数 ============


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器单例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_websocket_handler() -> WebSocketHandler:
    """获取 WebSocket 处理器单例"""
    global _websocket_handler
    if _websocket_handler is None:
        _websocket_handler = WebSocketHandler(get_connection_manager())
    return _websocket_handler


async def get_tts_adapter():
    """获取 TTS 适配器"""
    config = get_config()
    return await TTSAdapterFactory.create(config)


async def get_asr_engine():
    """获取 ASR 引擎"""
    config = get_config()
    return await ASREngineFactory.create(config)


# ============ 健康检查端点 ============


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    健康检查端点

    返回服务状态和各组件就绪状态
    """
    config = get_config()
    manager = get_connection_manager()

    # 检查 ASR 就绪状态
    asr_ready = False
    with contextlib.suppress(Exception):
        asr = await get_asr_engine()
        asr_ready = asr is not None

    # 检查 TTS 就绪状态
    tts_ready = False
    with contextlib.suppress(Exception):
        tts = await get_tts_adapter()
        tts_ready = tts is not None

    return HealthResponse(
        status="healthy",
        version="0.2.0",
        inference_mode=config.inference_mode.value,
        asr_provider=config.asr.provider.value,
        tts_provider=config.tts.provider.value,
        asr_ready=asr_ready,
        tts_ready=tts_ready,
        websocket_connections=manager.connection_count,
    )


@router.get("/config", response_model=ConfigResponse, tags=["System"])
async def get_service_config():
    """
    获取服务配置信息
    """
    config = get_config()

    # 获取可用角色列表
    available_characters: list[str] = []
    with contextlib.suppress(Exception):
        # 尝试获取预定义角色列表
        available_characters = ["mika", "feibi"]  # 默认角色

    return ConfigResponse(
        inference_mode=config.inference_mode.value,
        asr={
            "provider": config.asr.provider.value,
            "model": config.asr.model_name,
            "language": config.asr.language,
        },
        tts={
            "provider": config.tts.provider.value,
            "default_character": config.tts.default_character,
            "sample_rate": config.tts.sample_rate,
        },
        websocket={
            "max_connections": config.websocket.max_connections,
            "heartbeat_interval": config.websocket.heartbeat_interval,
        },
        available_characters=available_characters,
    )


# ============ TTS 端点 ============


@router.post("/tts/synthesize", tags=["TTS"])
async def synthesize_speech(request: TTSRequest):
    """
    文本转语音合成

    支持流式和非流式两种模式：
    - 非流式：返回完整音频的 base64 编码
    - 流式：返回音频流（chunked transfer）
    """
    try:
        adapter = await get_tts_adapter()

        if request.stream:
            # 流式模式
            async def audio_stream():
                async for chunk in adapter.synthesize_stream(
                    text=request.text, character=request.character, speed=request.speed
                ):
                    yield chunk

            content_type = {"wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg"}.get(
                request.format, "audio/wav"
            )

            return StreamingResponse(
                audio_stream(),
                media_type=content_type,
                headers={"X-Character": request.character, "X-Speed": str(request.speed)},
            )
        else:
            # 非流式模式
            result = await adapter.synthesize(
                text=request.text, character=request.character, speed=request.speed
            )

            if not result.success:
                raise HTTPException(status_code=500, detail=result.error or "合成失败")

            # 编码为 base64
            audio_base64 = base64.b64encode(result.audio_data).decode("utf-8")

            return TTSResponse(
                success=True,
                audio_base64=audio_base64,
                sample_rate=result.sample_rate,
                duration=result.duration,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 合成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tts/synthesize/audio", tags=["TTS"])
async def synthesize_speech_audio(request: TTSRequest):
    """
    文本转语音合成（直接返回音频文件）

    适用于需要直接获取音频文件的场景
    """
    try:
        adapter = await get_tts_adapter()

        result = await adapter.synthesize(
            text=request.text, character=request.character, speed=request.speed
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error or "合成失败")

        content_type = {"wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg"}.get(
            request.format, "audio/wav"
        )

        return Response(
            content=result.audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=tts_output.{request.format}",
                "X-Duration": str(result.duration) if result.duration else "",
                "X-Sample-Rate": str(result.sample_rate),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 合成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/tts/characters", tags=["TTS"])
async def list_characters():
    """
    获取可用的 TTS 角色列表
    """
    try:
        adapter = await get_tts_adapter()
        characters = await adapter.list_characters()

        return {"success": True, "characters": characters}
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        return {"success": False, "characters": [], "error": str(e)}


# ============ ASR 端点 ============


@router.post("/asr/transcribe", response_model=ASRResponse, tags=["ASR"])
async def transcribe_audio(request: ASRRequest):
    """
    语音转文本（Base64 音频输入）
    """
    try:
        engine = await get_asr_engine()

        # 解码 base64 音频
        audio_data = base64.b64decode(request.audio_base64)

        start_time = time.time()
        result = await engine.transcribe(
            audio=audio_data, sample_rate=request.sample_rate, language=request.language
        )
        duration = time.time() - start_time

        return ASRResponse(
            success=True,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            duration=duration,
        )

    except Exception as e:
        logger.error(f"ASR 识别失败: {e}")
        return ASRResponse(success=False, error=str(e))


@router.post("/asr/transcribe/upload", response_model=ASRResponse, tags=["ASR"])
async def transcribe_audio_file(
    file: Annotated[UploadFile, File()],
    language: Annotated[str | None, Form()] = None,
    sample_rate: Annotated[int, Form()] = 16000,
):
    """
    语音转文本（文件上传）

    支持 WAV、MP3、FLAC 等常见音频格式
    """
    try:
        engine = await get_asr_engine()

        # 读取上传的文件
        audio_data = await file.read()

        start_time = time.time()
        result = await engine.transcribe(
            audio=audio_data, sample_rate=sample_rate, language=language
        )
        duration = time.time() - start_time

        return ASRResponse(
            success=True,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            duration=duration,
        )

    except Exception as e:
        logger.error(f"ASR 识别失败: {e}")
        return ASRResponse(success=False, error=str(e))


# ============ WebSocket 端点 ============


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


# ============ 设置函数 ============


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


# ============ 兼容旧版 Genie-TTS API ============


@router.post("/tts", tags=["Legacy"])
async def legacy_tts(
    text: str = Form(...),
    character: str = Form(default="mika"),
    speed: float = Form(default=1.0),
):
    """
    兼容旧版 Genie-TTS API

    直接返回音频文件
    """
    request = TTSRequest(text=text, character=character, speed=speed, format="wav", stream=False)
    return await synthesize_speech_audio(request)
