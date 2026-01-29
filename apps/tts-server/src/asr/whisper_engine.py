"""
Whisper 引擎实现
基于 OpenAI Whisper 的本地 ASR 引擎
"""

import asyncio
import contextlib
import gc
import logging
from collections.abc import AsyncIterator
from typing import Literal

import numpy as np

from .base import ASREngine, ASRLanguage, ASRResult, AudioChunk
from .whisper_stream import resample_audio, stream_transcribe

logger = logging.getLogger(__name__)


# 语言映射
LANGUAGE_MAP = {
    ASRLanguage.CHINESE: "zh",
    ASRLanguage.JAPANESE: "ja",
    ASRLanguage.ENGLISH: "en",
    ASRLanguage.AUTO: None,
}


class WhisperEngine(ASREngine):
    """
    Whisper 引擎

    支持的模型:
    - tiny, base, small, medium, large, large-v2, large-v3
    - turbo (faster-whisper 专用)

    实现方式:
    - openai-whisper: 原版 Whisper
    - faster-whisper: CTranslate2 优化版本（推荐）
    """

    ModelSize = Literal["tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo"]

    def __init__(
        self,
        model_size: ModelSize = "large-v3",
        language: ASRLanguage = ASRLanguage.AUTO,
        device: str = "cuda",  # cuda, cpu, auto
        compute_type: str = "float16",  # float16, int8, int8_float16
        use_faster_whisper: bool = True,
        beam_size: int = 5,
        vad_filter: bool = True,
        cache_dir: str | None = None,
    ):
        super().__init__(language)
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.use_faster_whisper = use_faster_whisper
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self.cache_dir = cache_dir

        self._model = None
        self._processor = None  # 用于原版 whisper

    async def load(self) -> None:
        """加载 Whisper 模型"""
        if self._is_loaded:
            return

        logger.info(f"Loading Whisper model: {self.model_size} (faster={self.use_faster_whisper})")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)

        self._is_loaded = True
        logger.info("Whisper model loaded successfully")

    def _load_sync(self) -> None:
        """同步加载模型"""
        if self.use_faster_whisper:
            self._load_faster_whisper()
        else:
            self._load_openai_whisper()

    def _load_faster_whisper(self) -> None:
        """加载 faster-whisper 模型"""
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError(
                "faster-whisper is not installed. Please install it with: "
                "pip install faster-whisper"
            ) from e

        device = self.device
        if device == "auto":
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"

        self._model = WhisperModel(
            self.model_size,
            device=device,
            compute_type=self.compute_type,
            download_root=self.cache_dir,
        )

    def _load_openai_whisper(self) -> None:
        """加载原版 Whisper 模型"""
        try:
            import whisper
        except ImportError as e:
            raise ImportError(
                "openai-whisper is not installed. Please install it with: "
                "pip install openai-whisper"
            ) from e

        self._model = whisper.load_model(
            self.model_size,
            device=self.device,
            download_root=self.cache_dir,
        )

    async def unload(self) -> None:
        """卸载模型"""
        if not self._is_loaded:
            return

        logger.info("Unloading Whisper model")

        self._model = None
        self._processor = None
        self._is_loaded = False

        gc.collect()

        with contextlib.suppress(ImportError):
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """离线转录"""
        if not self._is_loaded:
            await self.load()

        # 转换音频数据
        audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        # 重采样到 16000 Hz（Whisper 要求）
        if sample_rate != 16000:
            audio_array = resample_audio(audio_array, sample_rate, 16000)

        # 确定语言
        lang = language or self.language
        whisper_lang = LANGUAGE_MAP.get(lang)

        loop = asyncio.get_event_loop()

        if self.use_faster_whisper:
            result = await loop.run_in_executor(
                None,
                self._transcribe_faster_whisper,
                audio_array,
                whisper_lang,
            )
        else:
            result = await loop.run_in_executor(
                None,
                self._transcribe_openai_whisper,
                audio_array,
                whisper_lang,
            )

        return result

    def _transcribe_faster_whisper(
        self,
        audio: np.ndarray,
        language: str | None,
    ) -> ASRResult:
        """使用 faster-whisper 转录"""
        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            word_timestamps=True,
        )

        # 收集所有分段
        text_parts = []
        words = []

        for segment in segments:
            text_parts.append(segment.text)

            if segment.words:
                for word in segment.words:
                    words.append(
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                        }
                    )

        text = "".join(text_parts).strip()

        return ASRResult(
            text=text,
            language=info.language or "unknown",
            confidence=1.0 - (info.language_probability or 0.0)
            if info.language_probability
            else 1.0,
            is_final=True,
            words=words,
        )

    def _transcribe_openai_whisper(
        self,
        audio: np.ndarray,
        language: str | None,
    ) -> ASRResult:
        """使用原版 Whisper 转录"""
        options = {
            "beam_size": self.beam_size,
            "word_timestamps": True,
        }

        if language:
            options["language"] = language

        result = self._model.transcribe(audio, **options)

        text = result.get("text", "").strip()
        detected_lang = result.get("language", "unknown")

        # 提取词级别时间戳
        words = []
        segments = result.get("segments", [])
        for segment in segments:
            segment_words = segment.get("words", [])
            for w in segment_words:
                words.append(
                    {
                        "word": w.get("word", ""),
                        "start": w.get("start", 0.0),
                        "end": w.get("end", 0.0),
                    }
                )

        return ASRResult(
            text=text,
            language=detected_lang,
            confidence=1.0,
            is_final=True,
            words=words,
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        language: ASRLanguage | None = None,
    ) -> AsyncIterator[ASRResult]:
        """Stream transcription using buffered windows."""
        async for result in stream_transcribe(self, audio_stream, language):
            yield result
