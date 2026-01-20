"""
Emotion rule base types and helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from .types import EmotionType


@dataclass
class EmotionContext:
    """Context passed through emotion rules."""

    text: str
    clean_text: str
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class EmotionRuleResult:
    """Result produced by a rule."""

    scores: dict[EmotionType, float] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)


class EmotionRule(Protocol):
    """Rule protocol for emotion scoring."""

    name: str

    def apply(self, context: EmotionContext) -> EmotionRuleResult:
        """Apply the rule to the context."""


class KeywordMatcherMixin:
    """Shared helpers for keyword matching."""

    def _compile_keyword(self, keyword: str) -> re.Pattern:
        if re.fullmatch(r"[a-zA-Z][a-zA-Z' -]*", keyword):
            return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
        return re.compile(re.escape(keyword), re.IGNORECASE)

    def _compile_phrase_pattern(self, phrases: list[str]) -> re.Pattern:
        escaped = [re.escape(p) for p in phrases if p]
        if not escaped:
            return re.compile(r"a^")
        return re.compile("|".join(escaped), re.IGNORECASE)
