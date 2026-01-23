"""Base classes for TTS adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


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
