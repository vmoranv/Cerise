"""Streaming utilities for Whisper."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

import numpy as np

from .base import ASRLanguage, ASRResult, AudioChunk


class WhisperEngineProtocol(Protocol):
    async def load(self) -> None:  # noqa: D401
        """Ensure the engine is loaded."""

    async def transcribe(
        self,
        audio: bytes,
        sample_rate: int = 16000,
        language: ASRLanguage | None = None,
    ) -> ASRResult:
        """Transcribe audio."""


async def stream_transcribe(
    engine: WhisperEngineProtocol,
    audio_stream: AsyncIterator[AudioChunk],
    language: ASRLanguage | None = None,
) -> AsyncIterator[ASRResult]:
    """Pseudo-streaming transcription using buffered windows."""
    await engine.load()

    buffer: list[np.ndarray] = []
    total_samples = 0
    sample_rate = 16000

    chunk_duration = 5.0
    overlap_duration = 1.0
    chunk_samples = int(chunk_duration * sample_rate)
    overlap_samples = int(overlap_duration * sample_rate)

    last_text = ""

    async for chunk in audio_stream:
        if chunk.is_end:
            if buffer:
                combined = np.concatenate(buffer)
                result = await engine.transcribe(
                    combined.astype(np.int16).tobytes(),
                    sample_rate,
                    language,
                )
                result.is_final = True
                yield result
            break

        audio_array = chunk.to_float32()

        if chunk.sample_rate != sample_rate:
            audio_array = resample_audio(audio_array, chunk.sample_rate, sample_rate)

        buffer.append(audio_array)
        total_samples += len(audio_array)

        if total_samples >= chunk_samples:
            combined = np.concatenate(buffer)

            result = await engine.transcribe(
                (combined * 32768).astype(np.int16).tobytes(),
                sample_rate,
                language,
            )

            if result.text != last_text:
                result.is_final = False
                yield result
                last_text = result.text

            if len(combined) > overlap_samples:
                buffer = [combined[-overlap_samples:]]
                total_samples = overlap_samples
            else:
                buffer = [combined]
                total_samples = len(combined)


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio to the target sample rate."""
    try:
        import soxr

        return soxr.resample(audio, orig_sr, target_sr)
    except ImportError:
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)
