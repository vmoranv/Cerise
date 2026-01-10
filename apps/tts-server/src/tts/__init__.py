"""
TTS 服务模块
"""

from .adapter import (
    CloudTTSAdapter,
    GenieTTSAdapter,
    TTSAdapter,
    TTSAdapterFactory,
    TTSResult,
    get_tts_adapter,
    shutdown_tts_adapter,
)

__all__ = [
    "TTSResult",
    "TTSAdapter",
    "GenieTTSAdapter",
    "CloudTTSAdapter",
    "TTSAdapterFactory",
    "get_tts_adapter",
    "shutdown_tts_adapter",
]
