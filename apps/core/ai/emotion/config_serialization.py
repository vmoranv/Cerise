"""
Emotion configuration serialization helpers.
"""

from __future__ import annotations

from typing import Any

from .config_models import EmotionConfig, EmotionLexiconConfig, EmotionRulesConfig


def emotion_defaults_to_dict(config: EmotionConfig) -> dict[str, Any]:
    return {
        "lexicon": _lexicon_to_dict(config.lexicon),
        "rules": _rules_to_dict(config.rules),
        "plugins_dir": config.plugins_dir,
        "plugin_glob": config.plugin_glob,
        "plugins": list(config.plugins),
    }


def _lexicon_to_dict(config: EmotionLexiconConfig) -> dict[str, Any]:
    return {
        "path": config.path,
        "keywords": config.keywords,
        "intensifiers": list(config.intensifiers),
        "diminishers": list(config.diminishers),
        "negations": list(config.negations),
        "positive_hints": list(config.positive_hints),
        "negative_hints": list(config.negative_hints),
    }


def _rules_to_dict(config: EmotionRulesConfig) -> dict[str, Any]:
    return {
        "enabled": list(config.enabled),
        "disabled": list(config.disabled),
        "custom": [
            {
                "name": rule.name,
                "emotion": rule.emotion,
                "weight": rule.weight,
                "patterns": list(rule.patterns),
                "kind": rule.kind,
                "priority": rule.priority,
            }
            for rule in config.custom
        ],
    }
