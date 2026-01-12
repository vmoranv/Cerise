"""
Emotion pipeline orchestration.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from ...infrastructure import Event, MessageBus
from .rules import EmotionContext, EmotionRule
from .types import EmotionResult, EmotionType

DEFAULT_OUTPUT_MAP: dict[EmotionType, EmotionType] = {
    EmotionType.FEARFUL: EmotionType.CONFUSED,
    EmotionType.DISGUSTED: EmotionType.ANGRY,
}


VAD_VALUES: dict[EmotionType, tuple[float, float, float]] = {
    EmotionType.NEUTRAL: (0.0, 0.3, 0.5),
    EmotionType.HAPPY: (0.8, 0.6, 0.7),
    EmotionType.SAD: (-0.7, 0.3, 0.3),
    EmotionType.ANGRY: (-0.6, 0.8, 0.8),
    EmotionType.SURPRISED: (0.3, 0.8, 0.4),
    EmotionType.FEARFUL: (-0.8, 0.7, 0.2),
    EmotionType.DISGUSTED: (-0.7, 0.5, 0.6),
    EmotionType.EXCITED: (0.7, 0.9, 0.7),
    EmotionType.CURIOUS: (0.4, 0.5, 0.5),
    EmotionType.CONFUSED: (-0.2, 0.5, 0.3),
    EmotionType.SHY: (0.1, 0.4, 0.2),
    EmotionType.SLEEPY: (-0.1, 0.1, 0.3),
}


@dataclass
class EmotionPipeline:
    """Pipeline that composes multiple emotion rules."""

    rules: Iterable[EmotionRule]
    bus: MessageBus | None = None
    output_map: dict[EmotionType, EmotionType] = field(default_factory=lambda: DEFAULT_OUTPUT_MAP.copy())

    def analyze(self, text: str) -> EmotionResult:
        clean_text = self._strip_thinking(text).strip()
        if not clean_text:
            return self._neutral_result()

        context = EmotionContext(text=text, clean_text=clean_text)
        scores: dict[EmotionType, float] = defaultdict(float)
        keywords: list[str] = []

        if self.bus:
            self.bus.publish_sync(
                Event(
                    type="emotion.analysis.started",
                    data={"text_length": len(clean_text)},
                    source="emotion_pipeline",
                )
            )

        for rule in self.rules:
            result = rule.apply(context)
            for emotion, score in result.scores.items():
                scores[emotion] += score
            if result.keywords:
                keywords.extend(result.keywords)
            if result.flags:
                context.flags.update(result.flags)
            if self.bus:
                self.bus.publish_sync(
                    Event(
                        type="emotion.rule.scored",
                        data={
                            "rule": getattr(rule, "name", rule.__class__.__name__),
                            "scores": {k.value: v for k, v in result.scores.items()},
                        },
                        source="emotion_pipeline",
                    )
                )

        result = self._build_result(scores, keywords)

        if self.bus:
            self.bus.publish_sync(
                Event(
                    type="emotion.analysis.completed",
                    data={
                        "primary": result.primary_emotion.value,
                        "confidence": result.confidence,
                    },
                    source="emotion_pipeline",
                )
            )

        return result

    def _strip_thinking(self, text: str) -> str:
        return re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.DOTALL | re.IGNORECASE)

    def _build_result(
        self,
        scores: dict[EmotionType, float],
        keywords: list[str],
    ) -> EmotionResult:
        positive_scores = {e: s for e, s in scores.items() if s > 0}
        if not positive_scores:
            return self._neutral_result()

        total_score = sum(positive_scores.values())
        normalized = {e: s / total_score for e, s in positive_scores.items()}
        raw_primary = max(normalized, key=normalized.get)
        confidence = self._confidence_from_scores(raw_primary, normalized, total_score)
        primary = self.output_map.get(raw_primary, raw_primary)

        valence, arousal, dominance = self._vad_from_scores(normalized)
        secondary = {e: score for e, score in normalized.items() if e != raw_primary and score >= 0.18}

        return EmotionResult(
            primary_emotion=primary,
            confidence=confidence,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            secondary_emotions=secondary,
            keywords=sorted(set(keywords)),
        )

    def _confidence_from_scores(
        self,
        primary: EmotionType,
        normalized: dict[EmotionType, float],
        total_score: float,
    ) -> float:
        base = normalized.get(primary, 0.0)
        strength = min(1.0, total_score / 3.0)
        return max(0.3, min(0.95, 0.35 + 0.65 * base * strength))

    def _vad_from_scores(self, normalized: dict[EmotionType, float]) -> tuple[float, float, float]:
        valence = 0.0
        arousal = 0.0
        dominance = 0.0
        for emotion, score in normalized.items():
            v, a, d = VAD_VALUES[emotion]
            valence += v * score
            arousal += a * score
            dominance += d * score
        return valence, arousal, dominance

    def _neutral_result(self) -> EmotionResult:
        v, a, d = VAD_VALUES[EmotionType.NEUTRAL]
        return EmotionResult(
            primary_emotion=EmotionType.NEUTRAL,
            confidence=1.0,
            valence=v,
            arousal=a,
            dominance=d,
        )
