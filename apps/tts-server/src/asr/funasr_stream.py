"""Streaming helpers for FunASR."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

import numpy as np

from .base import ASRLanguage, ASRResult, AudioChunk


class FunASREngineProtocol(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """Transcribe audio."""


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio to the target sample rate."""
    try:
        import soxr

        return soxr.resample(audio, orig_sr, target_sr)
    except ImportError:
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)


async def transcribe_stream_buffered(
    engine: FunASREngineProtocol,
    audio_stream: AsyncIterator[AudioChunk],
    language: ASRLanguage | None = None,
) -> AsyncIterator[ASRResult]:
    """Buffered streaming fallback when online model is unavailable."""
    buffer: list[bytes] = []
    total_duration = 0.0
    last_process_time = 0.0
    process_interval = 2.0

    async for chunk in audio_stream:
        if chunk.is_end:
            if buffer:
                combined = b"".join(buffer)
                result = await engine.transcribe(combined, chunk.sample_rate, language)
                result.is_final = True
                yield result
            break

        buffer.append(chunk.data)
        chunk_duration = len(chunk.data) / (chunk.sample_rate * 2)
        total_duration += chunk_duration

        if total_duration - last_process_time >= process_interval:
            combined = b"".join(buffer)
            result = await engine.transcribe(combined, chunk.sample_rate, language)
            result.is_final = False
            yield result
            last_process_time = total_duration
