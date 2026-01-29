"""Emotion event contracts."""

from __future__ import annotations

from typing import TypedDict

EMOTION_ANALYSIS_STARTED = "emotion.analysis.started"
EMOTION_RULE_SCORED = "emotion.rule.scored"
EMOTION_ANALYSIS_COMPLETED = "emotion.analysis.completed"

CHARACTER_EMOTION_CHANGED = "character.emotion_changed"


class EmotionAnalysisStartedPayload(TypedDict):
    text_length: int


def build_emotion_analysis_started(text_length: int) -> EmotionAnalysisStartedPayload:
    return {"text_length": text_length}


class EmotionRuleScoredPayload(TypedDict):
    rule: str
    scores: dict[str, float]


def build_emotion_rule_scored(rule: str, scores: dict[str, float]) -> EmotionRuleScoredPayload:
    return {"rule": rule, "scores": scores}


class EmotionAnalysisCompletedPayload(TypedDict):
    primary: str
    confidence: float
    valence: float
    arousal: float
    dominance: float
    intensity: float


def build_emotion_analysis_completed(
    *,
    primary: str,
    confidence: float,
    valence: float,
    arousal: float,
    dominance: float,
    intensity: float,
) -> EmotionAnalysisCompletedPayload:
    return {
        "primary": primary,
        "confidence": confidence,
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "intensity": intensity,
    }


class CharacterEmotionChangedPayload(TypedDict):
    from_state: str
    to_state: str
    intensity: float


def build_character_emotion_changed(
    *,
    from_state: str,
    to_state: str,
    intensity: float,
) -> CharacterEmotionChangedPayload:
    return {"from_state": from_state, "to_state": to_state, "intensity": intensity}


__all__ = [
    "EMOTION_ANALYSIS_STARTED",
    "EMOTION_RULE_SCORED",
    "EMOTION_ANALYSIS_COMPLETED",
    "CHARACTER_EMOTION_CHANGED",
    "EmotionAnalysisStartedPayload",
    "EmotionRuleScoredPayload",
    "EmotionAnalysisCompletedPayload",
    "CharacterEmotionChangedPayload",
    "build_emotion_analysis_started",
    "build_emotion_rule_scored",
    "build_emotion_analysis_completed",
    "build_character_emotion_changed",
]
