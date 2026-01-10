"""
ASR 引擎基类
定义统一的 ASR 接口
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class ASRLanguage(str, Enum):
    """支持的语言"""

    CHINESE = "zh"
    JAPANESE = "ja"
    ENGLISH = "en"
    AUTO = "auto"  # 自动检测


@dataclass
class ASRResult:
    """ASR 识别结果"""

    text: str  # 识别的文本
    language: str | None = None  # 检测到的语言
    confidence: float = 1.0  # 置信度 (0-1)
    is_final: bool = True  # 是否为最终结果（流式识别时）
    start_time: float | None = None  # 开始时间（秒）
    end_time: float | None = None  # 结束时间（秒）
    words: list[dict] = field(
        default_factory=list
    )  # 词级别信息 [{"word": "...", "start": 0.0, "end": 0.5}]

    def __str__(self) -> str:
        return self.text


@dataclass
class AudioChunk:
    """音频数据块"""

    data: bytes  # 原始音频数据
    sample_rate: int = 16000  # 采样率
    channels: int = 1  # 通道数
    dtype: str = "int16"  # 数据类型
    is_end: bool = False  # 是否为结束标记

    def to_numpy(self) -> np.ndarray:
        """转换为 numpy 数组"""
        dtype_map = {
            "int16": np.int16,
            "int32": np.int32,
            "float32": np.float32,
        }
        return np.frombuffer(self.data, dtype=dtype_map.get(self.dtype, np.int16))

    def to_float32(self) -> np.ndarray:
        """转换为 float32 格式（-1.0 到 1.0）"""
        arr = self.to_numpy()
        if self.dtype == "int16":
            return arr.astype(np.float32) / 32768.0
        elif self.dtype == "int32":
            return arr.astype(np.float32) / 2147483648.0
        else:
            return arr.astype(np.float32)


class ASREngine(ABC):
    """
    ASR 引擎抽象基类
    所有 ASR 实现都必须继承此类
    """

    def __init__(self, language: ASRLanguage = ASRLanguage.AUTO):
        self.language = language
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        """模型是否已加载"""
        return self._is_loaded

    @abstractmethod
    async def load(self) -> None:
        """
        加载模型
        异步方法，用于加载模型权重和初始化
        """

    @abstractmethod
    async def unload(self) -> None:
        """
        卸载模型
        释放 GPU/CPU 内存
        """

    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """
        离线转录

        Args:
            audio: 音频数据（PCM 格式）
            sample_rate: 采样率
            language: 语言（覆盖默认设置）

        Returns:
            ASRResult: 识别结果
        """

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
        language: ASRLanguage | None = None,
    ) -> AsyncIterator[ASRResult]:
        """
        流式转录

        Args:
            audio_stream: 音频数据流
            language: 语言（覆盖默认设置）

        Yields:
            ASRResult: 识别结果（包含中间结果和最终结果）
        """
        # This yield is required to make this an async generator
        # Implementations should override this method completely
        yield ASRResult(text="")  # type: ignore[misc]

    async def transcribe_file(
        self,
        file_path: str,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """
        从文件转录

        Args:
            file_path: 音频文件路径
            language: 语言

        Returns:
            ASRResult: 识别结果
        """
        import soundfile as sf

        audio, sample_rate = sf.read(file_path, dtype="int16")
        if len(audio.shape) > 1:
            audio = audio[:, 0]  # 取第一个通道

        return await self.transcribe(
            audio.tobytes(),
            sample_rate=sample_rate,
            language=language,
        )

    async def __aenter__(self):
        await self.load()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.unload()
