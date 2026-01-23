"""云端 ASR 客户端
支持多种云端 ASR API
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Literal

import httpx

from .base import ASREngine, ASRLanguage, ASRResult, AudioChunk
from .cloud_providers import CloudASRProviderMixin

logger = logging.getLogger(__name__)


class CloudASRClient(CloudASRProviderMixin, ASREngine):
    """
    云端 ASR 客户端基类
    支持 REST API 调用
    """

    Provider = Literal["azure", "google", "aws", "aliyun", "tencent", "baidu", "custom"]

    def __init__(
        self,
        provider: Provider = "custom",
        api_key: str | None = None,
        api_secret: str | None = None,
        api_url: str | None = None,
        region: str | None = None,
        language: ASRLanguage = ASRLanguage.AUTO,
        timeout: float = 30.0,
    ):
        super().__init__(language)
        self.provider = provider
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = api_url
        self.region = region
        self.timeout = timeout

        self._client: httpx.AsyncClient | None = None

    async def load(self) -> None:
        """初始化 HTTP 客户端"""
        if self._is_loaded:
            return

        self._client = httpx.AsyncClient(timeout=self.timeout)
        self._is_loaded = True
        logger.info(f"Cloud ASR client initialized: {self.provider}")

    async def unload(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._is_loaded = False

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """通过云端 API 转录"""
        if not self._is_loaded:
            await self.load()

        lang = language or self.language

        # 根据提供商调用不同的 API
        if self.provider == "aliyun":
            return await self._transcribe_aliyun(audio, sample_rate, lang)
        elif self.provider == "tencent":
            return await self._transcribe_tencent(audio, sample_rate, lang)
        elif self.provider == "baidu":
            return await self._transcribe_baidu(audio, sample_rate, lang)
        elif self.provider == "azure":
            return await self._transcribe_azure(audio, sample_rate, lang)
        elif self.provider == "custom":
            return await self._transcribe_custom(audio, sample_rate, lang)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        language: ASRLanguage | None = None,
    ) -> AsyncIterator[ASRResult]:
        """
        流式转录

        注意：大多数云端 API 不支持真正的流式识别，
        这里使用分块上传方案
        """
        if not self._is_loaded:
            await self.load()

        # 缓冲区
        buffer = []
        total_duration = 0.0
        process_interval = 3.0  # 每 3 秒处理一次
        last_process_time = 0.0

        async for chunk in audio_stream:
            if chunk.is_end:
                # 处理剩余数据
                if buffer:
                    combined = b"".join(buffer)
                    result = await self.transcribe(combined, chunk.sample_rate, language)
                    result.is_final = True
                    yield result
                break

            buffer.append(chunk.data)
            chunk_duration = len(chunk.data) / (chunk.sample_rate * 2)  # 16bit
            total_duration += chunk_duration

            if total_duration - last_process_time >= process_interval:
                combined = b"".join(buffer)
                result = await self.transcribe(combined, chunk.sample_rate, language)
                result.is_final = False
                yield result
                last_process_time = total_duration
