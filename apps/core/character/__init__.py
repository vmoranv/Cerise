# Character Module

"""
Cerise Character State - Emotion, motion, and personality management
"""

from .emotion import EmotionState, EmotionStateMachine
from .personality import PersonalityModel, PersonalityTrait

__all__ = [
    "EmotionState",
    "EmotionStateMachine",
    "PersonalityModel",
    "PersonalityTrait",
]
