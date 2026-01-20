"""
Emotion lexicon and modifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lexicon_keywords import DEFAULT_KEYWORDS
from .lexicon_modifiers import DIMINISHERS, INTENSIFIERS, NEGATIONS, NEGATIVE_HINTS, POSITIVE_HINTS
from .types import EmotionType


@dataclass(frozen=True)
class EmotionLexicon:
    """Lexicon and modifiers for emotion analysis."""

    keywords: dict[EmotionType, list[tuple[str, float]]]
    intensifiers: list[str]
    diminishers: list[str]
    negations: list[str]
    positive_hints: list[str]
    negative_hints: list[str]


DEFAULT_LEXICON = EmotionLexicon(
    keywords=DEFAULT_KEYWORDS,
    intensifiers=INTENSIFIERS,
    diminishers=DIMINISHERS,
    negations=NEGATIONS,
    positive_hints=POSITIVE_HINTS,
    negative_hints=NEGATIVE_HINTS,
)
