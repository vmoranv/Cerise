"""
Emotion configuration models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmotionLexiconConfig:
    """Lexicon config from yaml."""

    path: str = ""
    keywords: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    intensifiers: list[str] = field(default_factory=list)
    diminishers: list[str] = field(default_factory=list)
    negations: list[str] = field(default_factory=list)
    positive_hints: list[str] = field(default_factory=list)
    negative_hints: list[str] = field(default_factory=list)


@dataclass
class EmotionRuleConfig:
    """Custom rule config."""

    name: str
    emotion: str
    weight: float = 0.6
    patterns: list[str] = field(default_factory=list)
    kind: str = "regex"
    priority: int = 50


@dataclass
class EmotionRulesConfig:
    """Rules configuration."""

    enabled: list[str] = field(default_factory=list)
    disabled: list[str] = field(default_factory=list)
    custom: list[EmotionRuleConfig] = field(default_factory=list)


@dataclass
class EmotionConfig:
    """Overall emotion configuration."""

    lexicon: EmotionLexiconConfig = field(default_factory=EmotionLexiconConfig)
    rules: EmotionRulesConfig = field(default_factory=EmotionRulesConfig)
    plugins_dir: str = ""
    plugin_glob: str = "**/emotion/*.yaml"
    plugins: list[str] = field(default_factory=list)
