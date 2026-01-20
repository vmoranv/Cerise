# Character Emotion Module

"""
Emotion state management for character animation
"""

from .state_machine import EmotionStateMachine
from .types import EmotionState

__all__ = [
    "EmotionState",
    "EmotionStateMachine",
]
