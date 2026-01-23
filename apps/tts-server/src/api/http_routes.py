"""HTTP routes for the TTS server API."""

from __future__ import annotations

import base64
import contextlib
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from ..config import get_config
from .deps import get_asr_engine, get_connection_manager, get_tts_adapter
from .schemas import ASRRequest, ASRResponse, ConfigResponse, HealthResponse, TTSRequest, TTSResponse

logger = logging.getLogger(__name__)

router = APIRouter()


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
            "model": config.asr.get_model_name(),
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
