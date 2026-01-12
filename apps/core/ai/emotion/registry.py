"""
Emotion rule registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .lexicon import DEFAULT_LEXICON, EmotionLexicon
from .rules import EmoticonRule, EmotionRule, KeywordRule, PunctuationRule, SentimentHintRule


@dataclass
class EmotionRuleRegistry:
    """Registry for emotion rules with priority ordering."""

    _rules: list[tuple[int, EmotionRule]] = field(default_factory=list)

    def register(self, rule: EmotionRule, priority: int = 100) -> None:
        self._rules.append((priority, rule))
        self._rules.sort(key=lambda item: item[0])

    def extend(self, rules: list[tuple[int, EmotionRule]]) -> None:
        self._rules.extend(rules)
        self._rules.sort(key=lambda item: item[0])

    def build(self) -> list[EmotionRule]:
        return [rule for _, rule in self._rules]

    @classmethod
    def default(cls, lexicon: EmotionLexicon | None = None) -> EmotionRuleRegistry:
        lex = lexicon or DEFAULT_LEXICON
        registry = cls()
        registry.register(SentimentHintRule(lex), priority=10)
        registry.register(KeywordRule(lex), priority=20)
        registry.register(PunctuationRule(), priority=30)
        registry.register(EmoticonRule(), priority=40)
        return registry
