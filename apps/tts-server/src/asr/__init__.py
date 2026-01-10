"""
ASR（自动语音识别）模块
支持多种 ASR 引擎和云端 API
"""

from .base import ASREngine, ASRResult
from .factory import create_asr_engine

__all__ = ["ASREngine", "ASRResult", "create_asr_engine"]
