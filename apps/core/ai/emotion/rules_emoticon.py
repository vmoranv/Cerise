"""
Emoticon-based emotion rule.
"""

import re

from .rules_base import EmotionContext, EmotionRuleResult
from .types import EmotionType


class EmoticonRule:
    """Score emotions based on emoticons and stylized tokens."""

    name = "emoticon"

    def __init__(self):
        self._laugh_pattern = re.compile(r"(ha){2,}|(haha)+|[哈]{2,}|w{2,}|lol+", re.IGNORECASE)
        self._cry_pattern = re.compile(r"(T_T|Q_Q|QAQ|;_;|:'\(|:'-\()|[呜哭]{2,}", re.IGNORECASE)
        self._sigh_pattern = re.compile(r"(唉|哎|唔|哼)")
        self._orz_pattern = re.compile(r"\b(?:orz|otz)\b", re.IGNORECASE)
        self._sleepy_pattern = re.compile(r"\bzz+\b", re.IGNORECASE)

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        scores: dict[EmotionType, float] = {}
        text = context.clean_text
        if not text:
            return EmotionRuleResult()

        if self._laugh_pattern.search(text):
            scores[EmotionType.HAPPY] = scores.get(EmotionType.HAPPY, 0.0) + 0.8
            scores[EmotionType.EXCITED] = scores.get(EmotionType.EXCITED, 0.0) + 0.4

        if self._cry_pattern.search(text):
            scores[EmotionType.SAD] = scores.get(EmotionType.SAD, 0.0) + 0.8

        if self._sigh_pattern.search(text):
            scores[EmotionType.SAD] = scores.get(EmotionType.SAD, 0.0) + 0.4
            scores[EmotionType.SLEEPY] = scores.get(EmotionType.SLEEPY, 0.0) + 0.2

        if self._orz_pattern.search(text):
            scores[EmotionType.SAD] = scores.get(EmotionType.SAD, 0.0) + 0.5

        if self._sleepy_pattern.search(text):
            scores[EmotionType.SLEEPY] = scores.get(EmotionType.SLEEPY, 0.0) + 0.6

        return EmotionRuleResult(scores=scores)
