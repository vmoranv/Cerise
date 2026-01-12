"""
Emotion Types and Results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EmotionType(Enum):
    """Primary emotion types"""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    EXCITED = "excited"
    CURIOUS = "curious"
    CONFUSED = "confused"
    SHY = "shy"
    SLEEPY = "sleepy"


@dataclass
class EmotionResult:
    """Result of emotion analysis"""

    primary_emotion: EmotionType
    confidence: float  # 0.0 to 1.0
    valence: float  # -1.0 (negative) to 1.0 (positive)
    arousal: float  # 0.0 (calm) to 1.0 (excited)
    dominance: float  # 0.0 (submissive) to 1.0 (dominant)
    secondary_emotions: dict[EmotionType, float] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "primary_emotion": self.primary_emotion.value,
            "confidence": self.confidence,
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "secondary_emotions": {k.value: v for k, v in self.secondary_emotions.items()},
            "keywords": self.keywords,
        }
