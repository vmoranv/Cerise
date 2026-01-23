"""Genie-TTS adapter implementation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from .base import TTSAdapter, TTSResult

logger = logging.getLogger(__name__)


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
