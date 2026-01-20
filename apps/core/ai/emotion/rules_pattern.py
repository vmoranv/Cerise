"""
Pattern-based emotion rule.
"""

from __future__ import annotations

import re

from .rules_base import EmotionContext, EmotionRuleResult, KeywordMatcherMixin
from .types import EmotionType


class PatternRule(KeywordMatcherMixin):
    """Custom pattern rule configured at runtime."""

    def __init__(
        self,
        *,
        name: str,
        emotion: EmotionType,
        patterns: list[str],
        weight: float = 0.6,
        kind: str = "regex",
    ):
        self.name = name
        self._emotion = emotion
        self._weight = weight
        self._kind = kind
        if kind == "contains":
            self._patterns = [pattern.lower() for pattern in patterns if pattern]
        else:
            self._patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns if pattern]

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        text = context.clean_text
        if not text:
            return EmotionRuleResult()
        scores: dict[EmotionType, float] = {}
        keywords: list[str] = []
        if self._kind == "contains":
            lowered = text.lower()
            for pattern in self._patterns:
                if pattern in lowered:
                    scores[self._emotion] = scores.get(self._emotion, 0.0) + self._weight
                    keywords.append(pattern)
        else:
            for pattern in self._patterns:
                matches = list(pattern.finditer(text))
                if not matches:
                    continue
                scores[self._emotion] = scores.get(self._emotion, 0.0) + self._weight * len(matches)
                keywords.extend([match.group(0) for match in matches])
        return EmotionRuleResult(scores=scores, keywords=keywords)
