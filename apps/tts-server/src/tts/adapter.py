"""
TTS 适配器
统一封装本地 Genie-TTS 和云端 TTS API
"""

import asyncio
import base64
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from ..config import InferenceMode, TTSConfig, TTSProvider

logger = logging.getLogger(__name__)

# 全局 TTS 实例
_tts_adapter: "TTSAdapter | None" = None


@dataclass
class TTSResult:
    """TTS 合成结果"""

    audio: bytes
    sample_rate: int = 32000
    format: str = "wav"
    duration: float | None = None


class TTSAdapter(ABC):
    """TTS 适配器抽象基类"""

    @abstractmethod
    async def load(self) -> None:
        """加载模型"""
        pass

    @abstractmethod
    async def unload(self) -> None:
        """卸载模型"""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        character: str = "mika",
        speed: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """
        合成语音

        Args:
            text: 要合成的文本
            character: 角色名称
            speed: 语速，1.0 为正常速度

        Returns:
            TTSResult: 合成结果
        """
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        character: str = "mika",
        speed: float = 1.0,
        **kwargs,
    ) -> AsyncIterator[bytes]:
        """
        流式合成语音

        Args:
            text: 要合成的文本
            character: 角色名称
            speed: 语速

        Yields:
            音频数据块
        """
        pass

    @abstractmethod
    def list_characters(self) -> list:
        """获取可用角色列表"""
        pass


class GenieTTSAdapter(TTSAdapter):
    """
    Genie-TTS 本地适配器

    封装 genie_tts 库，提供异步接口
    """

    def __init__(
        self,
        device: str = "cpu",
        model_path: str | None = None,
        characters: list | None = None,
    ):
        self.device = device
        self.model_path = model_path
        self.characters = characters or ["mika", "feibi"]

        self._genie = None
        self._loaded_characters: set = set()
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """加载 Genie-TTS"""
        try:
            import genie_tts as genie

            self._genie = genie

            # 预加载默认角色
            for char in self.characters[:2]:  # 只预加载前两个
                await self._load_character(char)

            logger.info("Genie-TTS loaded successfully")

        except ImportError as e:
            raise ImportError("genie-tts not installed. Run: pip install genie-tts") from e

    async def _load_character(self, character: str) -> None:
        """加载角色模型"""
        if character in self._loaded_characters:
            return

        async with self._lock:
            if character in self._loaded_characters:
                return

            try:
                # 在线程池中运行，避免阻塞
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._genie.load_predefined_character,
                    character,
                )
                self._loaded_characters.add(character)
                logger.info(f"Character loaded: {character}")
            except Exception as e:
                logger.error(f"Failed to load character {character}: {e}")
                raise

    async def unload(self) -> None:
        """卸载模型"""
        self._loaded_characters.clear()
        self._genie = None
        logger.info("Genie-TTS unloaded")

    async def synthesize(
        self,
        text: str,
        character: str = "mika",
        speed: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """合成语音"""
        if self._genie is None:
            await self.load()

        # 确保角色已加载
        await self._load_character(character)

        # 在线程池中运行 TTS
        loop = asyncio.get_event_loop()

        # 使用临时文件保存音频
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # 调用 genie_tts
            await loop.run_in_executor(
                None,
                lambda: self._genie.tts(
                    character_name=character,
                    text=text,
                    play=False,
                    save_path=temp_path,
                    speed=speed,
                ),
            )

            # 读取音频文件
            with open(temp_path, "rb") as f:
                audio_data = f.read()

            # 获取音频信息
            import wave

            with wave.open(temp_path, "rb") as wf:
                sample_rate = wf.getframerate()
                duration = wf.getnframes() / sample_rate

            return TTSResult(
                audio=audio_data,
                sample_rate=sample_rate,
                format="wav",
                duration=duration,
            )

        finally:
            # 清理临时文件
            import os

            try:
                os.unlink(temp_path)
            except Exception:
                pass

    async def synthesize_stream(
        self,
        text: str,
        character: str = "mika",
        speed: float = 1.0,
        chunk_size: int = 4096,
        **kwargs,
    ) -> AsyncIterator[bytes]:
        """
        流式合成语音

        注意：Genie-TTS 不支持真正的流式合成，
        这里通过分句合成模拟流式效果
        """
        import re

        # 分句
        sentences = re.split(r"([。！？\.!?])", text)
        merged_sentences = []

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            if sentence.strip():
                merged_sentences.append(sentence)

        if len(sentences) % 2 == 1 and sentences[-1].strip():
            merged_sentences.append(sentences[-1])

        if not merged_sentences:
            merged_sentences = [text]

        # 逐句合成并返回
        for sentence in merged_sentences:
            result = await self.synthesize(
                text=sentence,
                character=character,
                speed=speed,
                **kwargs,
            )

            # 分块返回音频数据
            audio = result.audio
            for i in range(0, len(audio), chunk_size):
                yield audio[i : i + chunk_size]

    def list_characters(self) -> list:
        """获取可用角色列表"""
        return list(self._loaded_characters) or self.characters


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


class TTSAdapterFactory:
    """TTS 适配器工厂"""

    @staticmethod
    def create(config: TTSConfig) -> TTSAdapter:
        """根据配置创建 TTS 适配器"""
        if config.mode == InferenceMode.CLOUD or config.provider == TTSProvider.CLOUD_API:
            return CloudTTSAdapter(
                provider=config.cloud_provider,
                api_key=config.cloud_api_key,
                api_url=config.cloud_api_url,
                region=config.cloud_region,
            )
        else:
            return GenieTTSAdapter(
                device=config.device,
                model_path=config.local_model_path,
                characters=config.characters,
            )


async def get_tts_adapter(config: TTSConfig) -> TTSAdapter:
    """获取全局 TTS 适配器（单例）"""
    global _tts_adapter

    if _tts_adapter is None:
        _tts_adapter = TTSAdapterFactory.create(config)
        await _tts_adapter.load()

    return _tts_adapter


async def shutdown_tts_adapter() -> None:
    """关闭全局 TTS 适配器"""
    global _tts_adapter

    if _tts_adapter is not None:
        await _tts_adapter.unload()
        _tts_adapter = None
