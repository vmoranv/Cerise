"""
Sentiment hint emotion rule.
"""

from .lexicon import EmotionLexicon
from .rules_base import EmotionContext, EmotionRuleResult, KeywordMatcherMixin
from .types import EmotionType


class SentimentHintRule(KeywordMatcherMixin):
    """Detect coarse positive/negative hints to bias other rules."""

    name = "sentiment_hint"

    def __init__(self, lexicon: EmotionLexicon):
        self._positive_pattern = self._compile_phrase_pattern(lexicon.positive_hints)
        self._negative_pattern = self._compile_phrase_pattern(lexicon.negative_hints)

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        flags: dict[str, bool] = {}
        scores: dict[EmotionType, float] = {}

        if self._positive_pattern.search(context.clean_text):
            flags["positive_hint"] = True
            scores[EmotionType.HAPPY] = scores.get(EmotionType.HAPPY, 0.0) + 0.2

        if self._negative_pattern.search(context.clean_text):
            flags["negative_hint"] = True
            scores[EmotionType.SAD] = scores.get(EmotionType.SAD, 0.0) + 0.2
            scores[EmotionType.ANGRY] = scores.get(EmotionType.ANGRY, 0.0) + 0.1

        return EmotionRuleResult(scores=scores, flags=flags)
