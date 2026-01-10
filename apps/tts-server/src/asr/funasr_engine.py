"""
FunASR 引擎实现
基于阿里巴巴 FunASR 框架的本地 ASR 引擎
"""

import asyncio
import contextlib
import gc
import logging
from collections.abc import AsyncIterator

import numpy as np

from .base import ASREngine, ASRLanguage, ASRResult, AudioChunk

logger = logging.getLogger(__name__)


class FunASREngine(ASREngine):
    """
    FunASR 引擎

    支持的模型:
    - paraformer-zh: 中文语音识别
    - paraformer-en: 英文语音识别
    - paraformer-large: 大模型，精度更高
    - sensevoice: 多语言情感识别
    """

    # 默认模型配置
    DEFAULT_MODEL = "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    DEFAULT_VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    DEFAULT_PUNC_MODEL = "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        vad_model: str | None = DEFAULT_VAD_MODEL,
        punc_model: str | None = DEFAULT_PUNC_MODEL,
        language: ASRLanguage = ASRLanguage.CHINESE,
        device: str = "cuda",  # cuda, cpu
        use_timestamp: bool = True,
        batch_size: int = 1,
        cache_dir: str | None = None,
    ):
        super().__init__(language)
        self.model_name = model_name
        self.vad_model = vad_model
        self.punc_model = punc_model
        self.device = device
        self.use_timestamp = use_timestamp
        self.batch_size = batch_size
        self.cache_dir = cache_dir

        self._model = None
        self._vad = None
        self._punc = None
        self._online_model = None  # 流式模型

    async def load(self) -> None:
        """加载 FunASR 模型"""
        if self._is_loaded:
            return

        logger.info(f"Loading FunASR model: {self.model_name}")

        # 在线程池中加载模型（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)

        self._is_loaded = True
        logger.info("FunASR model loaded successfully")

    def _load_sync(self) -> None:
        """同步加载模型"""
        try:
            from funasr import AutoModel
        except ImportError as e:
            raise ImportError(
                "FunASR is not installed. Please install it with: pip install funasr"
            ) from e

        model_kwargs = {
            "model": self.model_name,
            "device": self.device,
        }

        if self.vad_model:
            model_kwargs["vad_model"] = self.vad_model

        if self.punc_model:
            model_kwargs["punc_model"] = self.punc_model

        if self.cache_dir:
            model_kwargs["model_path"] = self.cache_dir

        self._model = AutoModel(**model_kwargs)

        # 加载流式模型（如果需要）
        try:
            self._online_model = AutoModel(
                model="iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
                device=self.device,
            )
        except Exception as e:
            logger.warning(f"Failed to load online model for streaming: {e}")
            self._online_model = None

    async def unload(self) -> None:
        """卸载模型"""
        if not self._is_loaded:
            return

        logger.info("Unloading FunASR model")

        self._model = None
        self._vad = None
        self._punc = None
        self._online_model = None
        self._is_loaded = False

        # 触发垃圾回收
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

        # 如果采样率不是 16000，需要重采样
        if sample_rate != 16000:
            audio_array = self._resample(audio_array, sample_rate, 16000)

        # 在线程池中执行推理
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._transcribe_sync, audio_array)

        return result

    def _transcribe_sync(self, audio_array: np.ndarray) -> ASRResult:
        """同步转录"""
        result = self._model.generate(
            input=audio_array,
            batch_size_s=300,  # 批处理时长（秒）
            hotword="",  # 热词
        )

        if not result:
            return ASRResult(text="", confidence=0.0)

        # 解析结果
        if isinstance(result, list) and len(result) > 0:
            res = result[0]
        else:
            res = result

        text = res.get("text", "")

        # 提取词级别时间戳
        words = []
        if "timestamp" in res and res["timestamp"]:
            timestamps = res["timestamp"]
            raw_text = res.get("raw_text", text)

            # FunASR 返回的 timestamp 格式: [[start_ms, end_ms], ...]
            if isinstance(timestamps, list):
                for i, (start_ms, end_ms) in enumerate(timestamps):
                    words.append(
                        {
                            "word": raw_text[i] if i < len(raw_text) else "",
                            "start": start_ms / 1000.0,
                            "end": end_ms / 1000.0,
                        }
                    )

        return ASRResult(
            text=text,
            language=self.language.value if self.language != ASRLanguage.AUTO else "zh",
            confidence=1.0,
            is_final=True,
            words=words,
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        language: ASRLanguage | None = None,
    ) -> AsyncIterator[ASRResult]:
        """流式转录"""
        if not self._is_loaded:
            await self.load()

        if self._online_model is None:
            # 回退到缓冲模式
            async for result in self._transcribe_stream_buffered(audio_stream, language):
                yield result
            return

        # 使用在线模型进行流式识别
        cache = {}
        buffer = []

        async for chunk in audio_stream:
            if chunk.is_end:
                # 处理剩余数据
                if buffer:
                    combined = np.concatenate(buffer)
                    result = await self._process_online_chunk(combined, cache, is_final=True)
                    if result:
                        yield result
                break

            # 转换音频
            audio_array = chunk.to_float32()
            buffer.append(audio_array)

            # 每 0.5 秒处理一次
            total_samples = sum(len(b) for b in buffer)
            if total_samples >= chunk.sample_rate * 0.5:
                combined = np.concatenate(buffer)
                buffer = []

                result = await self._process_online_chunk(combined, cache, is_final=False)
                if result:
                    yield result

    async def _process_online_chunk(
        self,
        audio: np.ndarray,
        cache: dict,
        is_final: bool,
    ) -> ASRResult | None:
        """处理在线音频块"""
        loop = asyncio.get_event_loop()

        def process():
            return self._online_model.generate(
                input=audio,
                cache=cache,
                is_final=is_final,
            )

        result = await loop.run_in_executor(None, process)

        if not result:
            return None

        if isinstance(result, list) and len(result) > 0:
            res = result[0]
        else:
            res = result

        text = res.get("text", "")
        if not text:
            return None

        return ASRResult(
            text=text,
            language=self.language.value if self.language != ASRLanguage.AUTO else "zh",
            confidence=1.0,
            is_final=is_final,
        )

    async def _transcribe_stream_buffered(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        language: ASRLanguage | None = None,
    ) -> AsyncIterator[ASRResult]:
        """缓冲模式的流式转录（当在线模型不可用时）"""
        buffer = []
        total_duration = 0.0
        last_process_time = 0.0
        process_interval = 2.0  # 每 2 秒处理一次

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
            chunk_duration = len(chunk.data) / (chunk.sample_rate * 2)  # 假设 16bit
            total_duration += chunk_duration

            # 定期处理
            if total_duration - last_process_time >= process_interval:
                combined = b"".join(buffer)
                result = await self.transcribe(combined, chunk.sample_rate, language)
                result.is_final = False
                yield result
                last_process_time = total_duration

    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """重采样音频"""
        try:
            import soxr

            return soxr.resample(audio, orig_sr, target_sr)
        except ImportError:
            # 使用简单的线性插值
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio)
