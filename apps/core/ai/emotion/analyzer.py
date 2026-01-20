"""
Emotion Analyzer

Dependency-injected wrapper around the emotion pipeline.
"""

from __future__ import annotations

from ...infrastructure import EventBus
from .lexicon import DEFAULT_LEXICON, EmotionLexicon
from .manager import EmotionConfigManager
from .pipeline import VAD_VALUES, EmotionPipeline
from .registry import EmotionRuleRegistry
from .rules import EmotionRule
from .types import EmotionResult, EmotionType


class EmotionAnalyzer:
    """Analyzes text for emotional content."""

    def __init__(
        self,
        *,
        pipeline: EmotionPipeline | None = None,
        rules: list[EmotionRule] | None = None,
        registry: EmotionRuleRegistry | None = None,
        lexicon: EmotionLexicon | None = None,
        bus: EventBus | None = None,
        manager: EmotionConfigManager | None = None,
        character: str | None = None,
    ):
        self._character = character or "default"
        self._manager = manager
        if pipeline is None and manager is None:
            if bus is None:
                raise ValueError("bus is required when no pipeline or manager is provided")
            lex = lexicon or DEFAULT_LEXICON
            if rules is None:
                registry = registry or EmotionRuleRegistry.default(lex)
                rules = registry.build()
            pipeline = EmotionPipeline(rules=rules, bus=bus)
        self._pipeline = pipeline

    def analyze(self, text: str, *, character: str | None = None) -> EmotionResult:
        """Analyze text for emotions."""
        pipeline = self._pipeline or self._get_pipeline(character)
        return pipeline.analyze(text)

    def analyze_for_character(self, text: str, *, character: str | None = None) -> str:
        """Get a simple emotion name for character animation."""
        result = self.analyze(text, character=character)
        return result.primary_emotion.value

    def blend_emotions(self, emotions: list[EmotionResult], weights: list[float] | None = None) -> EmotionResult:
        """Blend multiple emotion results."""
        if not emotions:
            v, a, d = VAD_VALUES[EmotionType.NEUTRAL]
            return EmotionResult(
                primary_emotion=EmotionType.NEUTRAL,
                confidence=1.0,
                valence=v,
                arousal=a,
                dominance=d,
            )

        if weights is None:
            weights = [1.0 / len(emotions)] * len(emotions)

        total_valence = sum(e.valence * w for e, w in zip(emotions, weights))
        total_arousal = sum(e.arousal * w for e, w in zip(emotions, weights))
        total_dominance = sum(e.dominance * w for e, w in zip(emotions, weights))

        best_emotion = EmotionType.NEUTRAL
        min_distance = float("inf")

        for emotion, (v, a, d) in VAD_VALUES.items():
            distance = (v - total_valence) ** 2 + (a - total_arousal) ** 2 + (d - total_dominance) ** 2
            if distance < min_distance:
                min_distance = distance
                best_emotion = emotion

        return EmotionResult(
            primary_emotion=best_emotion,
            confidence=max(e.confidence for e in emotions),
            valence=total_valence,
            arousal=total_arousal,
            dominance=total_dominance,
        )

    def _get_pipeline(self, character: str | None) -> EmotionPipeline:
        if not self._manager:
            if self._pipeline:
                return self._pipeline
            raise RuntimeError("Emotion pipeline is not configured")
        return self._manager.get_pipeline(character or self._character)
