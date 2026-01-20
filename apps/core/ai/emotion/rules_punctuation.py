"""
Punctuation-based emotion rule.
"""

import re

from .rules_base import EmotionContext, EmotionRuleResult
from .types import EmotionType


class PunctuationRule:
    """Score emotions based on punctuation cues."""

    name = "punctuation"

    def __init__(self):
        self._exclamation_pattern = re.compile(r"[!！]")
        self._question_pattern = re.compile(r"[?？]")
        self._surprise_punct_pattern = re.compile(r"[!?？！]{2,}")
        self._ellipsis_pattern = re.compile(r"(\.\.\.|…+|……)")

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        scores: dict[EmotionType, float] = {}
        text = context.clean_text
        if not text:
            return EmotionRuleResult()

        exclamations = len(self._exclamation_pattern.findall(text))
        questions = len(self._question_pattern.findall(text))

        if exclamations:
            bump = 0.2 + 0.1 * min(4, exclamations)
            if context.flags.get("negative_hint"):
                scores[EmotionType.ANGRY] = scores.get(EmotionType.ANGRY, 0.0) + bump
            else:
                scores[EmotionType.EXCITED] = scores.get(EmotionType.EXCITED, 0.0) + bump

        if questions:
            bump = 0.15 + 0.1 * min(3, questions)
            scores[EmotionType.CURIOUS] = scores.get(EmotionType.CURIOUS, 0.0) + bump
            if questions >= 2:
                scores[EmotionType.CONFUSED] = scores.get(EmotionType.CONFUSED, 0.0) + bump * 0.7

        if self._surprise_punct_pattern.search(text):
            scores[EmotionType.SURPRISED] = scores.get(EmotionType.SURPRISED, 0.0) + 0.6

        if self._ellipsis_pattern.search(text):
            scores[EmotionType.SAD] = scores.get(EmotionType.SAD, 0.0) + 0.2
            scores[EmotionType.CONFUSED] = scores.get(EmotionType.CONFUSED, 0.0) + 0.2

        return EmotionRuleResult(scores=scores)
