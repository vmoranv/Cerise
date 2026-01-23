"""Compatibility exports for TTS adapters."""

from .base import TTSAdapter, TTSResult
from .cloud_adapter import CloudTTSAdapter
from .factory import TTSAdapterFactory, get_tts_adapter, shutdown_tts_adapter
from .genie_adapter import GenieTTSAdapter

__all__ = [
    "TTSResult",
    "TTSAdapter",
    "GenieTTSAdapter",
    "CloudTTSAdapter",
    "TTSAdapterFactory",
    "get_tts_adapter",
    "shutdown_tts_adapter",
]
