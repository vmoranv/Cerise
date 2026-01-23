"""Cloud TTS adapter implementation."""

from __future__ import annotations

import base64
import logging
from collections.abc import AsyncIterator

from .base import TTSAdapter, TTSResult

logger = logging.getLogger(__name__)


class CloudTTSAdapter(TTSAdapter):
    """
    云端 TTS 适配器

    调用云端 TTS API 进行语音合成
    """

    def __init__(
        self,
        provider: str = "custom",
        api_key: str | None = None,
        api_url: str | None = None,
        **kwargs,
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_url = api_url
        self.extra_config = kwargs

        self._client = None

    async def load(self) -> None:
        """初始化 HTTP 客户端"""
        import httpx

        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"Cloud TTS client initialized: {self.provider}")

    async def unload(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def synthesize(
        self,
        text: str,
        character: str = "default",
        speed: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """调用云端 API 合成语音"""
        if self._client is None:
            await self.load()

        if self.provider == "azure":
            return await self._synthesize_azure(text, character, speed, **kwargs)
        elif self.provider == "aliyun":
            return await self._synthesize_aliyun(text, character, speed, **kwargs)
        elif self.provider == "tencent":
            return await self._synthesize_tencent(text, character, speed, **kwargs)
        else:
            return await self._synthesize_custom(text, character, speed, **kwargs)

    async def _synthesize_azure(
        self,
        text: str,
        voice: str,
        speed: float,
        **kwargs,
    ) -> TTSResult:
        """Azure 语音合成"""
        region = self.extra_config.get("region", "eastus")
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

        # SSML 格式
        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>
            <voice name='{voice}'>
                <prosody rate='{speed}'>
                    {text}
                </prosody>
            </voice>
        </speak>
        """

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",
        }

        response = await self._client.post(url, content=ssml, headers=headers)
        response.raise_for_status()

        return TTSResult(
            audio=response.content,
            sample_rate=24000,
            format="wav",
        )

    async def _synthesize_aliyun(
        self,
        text: str,
        voice: str,
        speed: float,
        **kwargs,
    ) -> TTSResult:
        """阿里云语音合成"""
        # 阿里云 TTS API
        url = self.api_url or "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/tts"

        params = {
            "appkey": self.extra_config.get("appkey", ""),
            "text": text,
            "voice": voice,
            "format": "wav",
            "sample_rate": 16000,
            "speech_rate": int((speed - 1) * 500),  # -500 到 500
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        response = await self._client.get(url, params=params, headers=headers)
        response.raise_for_status()

        return TTSResult(
            audio=response.content,
            sample_rate=16000,
            format="wav",
        )

    async def _synthesize_tencent(
        self,
        text: str,
        voice: str,
        speed: float,
        **kwargs,
    ) -> TTSResult:
        """腾讯云语音合成"""
        # 腾讯云 TTS API
        url = "https://tts.tencentcloudapi.com/"

        # 构建请求
        params = {
            "Action": "TextToVoice",
            "Version": "2019-08-23",
            "Text": text,
            "VoiceType": int(voice) if voice.isdigit() else 1001,
            "Speed": speed,
            "Codec": "wav",
            "SampleRate": 16000,
        }

        headers = {
            "Authorization": self._build_tencent_auth(params),
            "Content-Type": "application/json",
        }

        response = await self._client.post(url, json=params, headers=headers)
        response.raise_for_status()

        result = response.json()
        audio_data = base64.b64decode(result.get("Response", {}).get("Audio", ""))

        return TTSResult(
            audio=audio_data,
            sample_rate=16000,
            format="wav",
        )

    def _build_tencent_auth(self, params: dict) -> str:
        """构建腾讯云认证头（简化版）"""
        # 实际使用需要完整实现 TC3-HMAC-SHA256 签名
        return f"Bearer {self.api_key}"

    async def _synthesize_custom(
        self,
        text: str,
        voice: str,
        speed: float,
        **kwargs,
    ) -> TTSResult:
        """自定义 API 合成"""
        if not self.api_url:
            raise ValueError("Custom TTS API URL not configured")

        data = {
            "text": text,
            "voice": voice,
            "speed": speed,
            **kwargs,
        }

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = await self._client.post(self.api_url, json=data, headers=headers)
        response.raise_for_status()

        # 检查响应类型
        content_type = response.headers.get("content-type", "")

        if "audio" in content_type or "octet-stream" in content_type:
            return TTSResult(
                audio=response.content,
                sample_rate=self.extra_config.get("sample_rate", 16000),
                format=self.extra_config.get("format", "wav"),
            )
        else:
            # JSON 响应，音频在 base64 字段中
            result = response.json()
            audio_b64 = result.get("audio") or result.get("data", {}).get("audio", "")
            return TTSResult(
                audio=base64.b64decode(audio_b64),
                sample_rate=result.get("sample_rate", 16000),
                format=result.get("format", "wav"),
            )

    async def synthesize_stream(
        self,
        text: str,
        character: str = "default",
        speed: float = 1.0,
        chunk_size: int = 4096,
        **kwargs,
    ) -> AsyncIterator[bytes]:
        """流式合成（模拟）"""
        result = await self.synthesize(text, character, speed, **kwargs)

        audio = result.audio
        for i in range(0, len(audio), chunk_size):
            yield audio[i : i + chunk_size]

    def list_characters(self) -> list:
        """获取可用角色列表"""
        # 云端角色列表通常需要从 API 获取
        return self.extra_config.get("voices", ["default"])
