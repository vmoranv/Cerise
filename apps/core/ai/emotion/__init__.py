# Emotion Analysis Module

"""
Emotion analysis for text content
"""

from .analyzer import EmotionAnalyzer
from .config import EmotionConfig, load_emotion_config
from .manager import EmotionConfigManager
from .pipeline import EmotionPipeline
from .registry import EmotionRuleRegistry
from .types import EmotionResult, EmotionType

__all__ = [
    "EmotionAnalyzer",
    "EmotionConfig",
    "load_emotion_config",
    "EmotionConfigManager",
    "EmotionResult",
    "EmotionType",
    "EmotionPipeline",
    "EmotionRuleRegistry",
]
