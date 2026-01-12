"""
Emotion rules and mixins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from .lexicon import EmotionLexicon
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
