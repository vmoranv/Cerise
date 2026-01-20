"""
Rule helpers for emotion manager.
"""

from __future__ import annotations

from typing import Any

from .config_models import EmotionConfig
from .lexicon import EmotionLexicon
from .manager_lexicon import _emotion_from_key
from .rules import EmoticonRule, KeywordRule, PatternRule, PunctuationRule, SentimentHintRule


class RulesMixin:
    def _build_rules(self, config: EmotionConfig, lexicon: EmotionLexicon) -> list[Any]:
        rules_with_priority: list[tuple[int, Any]] = [
            (10, SentimentHintRule(lexicon)),
            (20, KeywordRule(lexicon)),
            (30, PunctuationRule()),
            (40, EmoticonRule()),
        ]

        if config.rules.enabled:
            enabled = {name.lower() for name in config.rules.enabled}
            rules_with_priority = [
                (priority, rule) for priority, rule in rules_with_priority if rule.name.lower() in enabled
            ]

        if config.rules.disabled:
            disabled = {name.lower() for name in config.rules.disabled}
            rules_with_priority = [
                (priority, rule) for priority, rule in rules_with_priority if rule.name.lower() not in disabled
            ]

        for rule_config in config.rules.custom:
            emotion = _emotion_from_key(rule_config.emotion)
            if not emotion:
                continue
            rules_with_priority.append(
                (
                    rule_config.priority,
                    PatternRule(
                        name=rule_config.name,
                        emotion=emotion,
                        patterns=rule_config.patterns,
                        weight=rule_config.weight,
                        kind=rule_config.kind,
                    ),
                )
            )

        rules_with_priority.sort(key=lambda item: item[0])
        return [rule for _, rule in rules_with_priority]
