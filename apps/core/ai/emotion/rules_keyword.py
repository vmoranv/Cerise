"""
Keyword-based emotion rules.
"""

from __future__ import annotations

import re

from .lexicon import EmotionLexicon
from .rules_base import EmotionContext, EmotionRuleResult, KeywordMatcherMixin
from .types import EmotionType


class KeywordRule(KeywordMatcherMixin):
    """Score emotions based on weighted keywords."""

    name = "keyword"

    NEGATION_MAP: dict[EmotionType, EmotionType] = {
        EmotionType.HAPPY: EmotionType.SAD,
        EmotionType.EXCITED: EmotionType.SAD,
        EmotionType.CURIOUS: EmotionType.CONFUSED,
        EmotionType.SURPRISED: EmotionType.NEUTRAL,
        EmotionType.ANGRY: EmotionType.NEUTRAL,
        EmotionType.SAD: EmotionType.NEUTRAL,
        EmotionType.FEARFUL: EmotionType.CONFUSED,
        EmotionType.DISGUSTED: EmotionType.ANGRY,
        EmotionType.SHY: EmotionType.NEUTRAL,
        EmotionType.SLEEPY: EmotionType.NEUTRAL,
    }

    def __init__(self, lexicon: EmotionLexicon):
        self._intensifier_pattern = self._compile_phrase_pattern(lexicon.intensifiers)
        self._diminisher_pattern = self._compile_phrase_pattern(lexicon.diminishers)
        self._negation_pattern = self._compile_phrase_pattern(lexicon.negations)
        self._compiled_keywords: dict[EmotionType, list[tuple[re.Pattern, str, float]]] = {}
        for emotion, keywords in lexicon.keywords.items():
            compiled = []
            for keyword, weight in keywords:
                compiled.append((self._compile_keyword(keyword), keyword, weight))
            self._compiled_keywords[emotion] = compiled

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        if not context.clean_text:
            return EmotionRuleResult()

        scores: dict[EmotionType, float] = {}
        keywords: list[str] = []

        for emotion, patterns in self._compiled_keywords.items():
            for pattern, keyword, weight in patterns:
                for match in pattern.finditer(context.clean_text):
                    multiplier = self._modifier_multiplier(context.clean_text, match.start(), match.group(0))
                    score = weight * multiplier
                    if self._is_negated(context.clean_text, match.start()):
                        target = self.NEGATION_MAP.get(emotion)
                        if target:
                            scores[target] = scores.get(target, 0.0) + score * 0.7
                        continue
                    scores[emotion] = scores.get(emotion, 0.0) + score
                    keywords.append(match.group(0))

        return EmotionRuleResult(scores=scores, keywords=keywords)

    def _modifier_multiplier(self, text: str, start: int, matched: str) -> float:
        window_start = max(0, start - 10)
        window = text[window_start:start].lower()
        multiplier = 1.0
        if self._intensifier_pattern.search(window):
            multiplier *= 1.4
        if self._diminisher_pattern.search(window):
            multiplier *= 0.7
        if matched.isupper() and len(matched) >= 3:
            multiplier *= 1.2
        return multiplier

    def _is_negated(self, text: str, start: int) -> bool:
        window_start = max(0, start - 8)
        window = text[window_start:start].lower()
        return bool(self._negation_pattern.search(window))
