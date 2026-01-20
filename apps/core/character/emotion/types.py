"""Emotion state types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EmotionState(Enum):
    """Character emotion states."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    EXCITED = "excited"
    CURIOUS = "curious"
    CONFUSED = "confused"
    SHY = "shy"
    SLEEPY = "sleepy"


@dataclass
class EmotionTransition:
    """Represents an emotion transition."""

    from_state: EmotionState
    to_state: EmotionState
    duration: float  # seconds
    easing: str = "ease-in-out"


@dataclass
class EmotionStateData:
    """Current emotion state data."""

    state: EmotionState
    intensity: float = 1.0  # 0.0 to 1.0
    blend_weight: float = 1.0  # For blending during transitions
    timestamp: datetime = field(default_factory=datetime.now)
