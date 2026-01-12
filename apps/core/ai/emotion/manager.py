"""
Emotion configuration manager with hot reload and per-character profiles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ...config.loader import get_data_dir
from ...infrastructure import MessageBus
from .config import (
    EmotionConfig,
    EmotionLexiconConfig,
    emotion_config_from_dict,
    lexicon_config_from_dict,
    load_emotion_config,
    merge_emotion_configs,
)
from .lexicon import DEFAULT_LEXICON, EmotionLexicon
from .pipeline import EmotionPipeline
from .rules import EmoticonRule, KeywordRule, PatternRule, PunctuationRule, SentimentHintRule
from .types import EmotionType

logger = logging.getLogger(__name__)


@dataclass
class _PipelineCache:
    pipeline: EmotionPipeline
    sources: list[Path]
    mtimes: dict[Path, float]


@dataclass
class _ConfigSource:
    config: EmotionConfig
    source_path: Path | None


class EmotionConfigManager:
    """Load emotion configs, support plugins, and hot reload per character."""

    def __init__(self, config_path: str | Path | None = None, bus: MessageBus | None = None):
        self._data_dir = Path(get_data_dir())
        self._config_path = Path(config_path) if config_path else self._data_dir / "emotion.yaml"
        self._bus = bus
        self._base_config = EmotionConfig()
        self._base_mtime = 0.0
        self._plugin_paths: set[Path] = set()
        self._cache: dict[str, _PipelineCache] = {}
        self._load_base_config()

    def register_plugin_path(self, path: str | Path) -> None:
        self._plugin_paths.add(Path(path))
        self._cache.clear()

    def get_pipeline(self, character: str | None = None) -> EmotionPipeline:
        profile_key = character or "default"
        self._load_base_config()
        merged_config, sources, config_chain = self._build_profile_config(character)
        cached = self._cache.get(profile_key)
        if cached and not self._sources_changed(cached, sources):
            return cached.pipeline
        pipeline = self._build_pipeline(merged_config, config_chain)
        self._cache[profile_key] = _PipelineCache(
            pipeline=pipeline,
            sources=sources,
            mtimes={path: path.stat().st_mtime for path in sources if path.exists()},
        )
        return pipeline

    def _load_base_config(self) -> None:
        if not self._config_path.exists():
            return
        mtime = self._config_path.stat().st_mtime
        if mtime <= self._base_mtime:
            return
        self._base_config = load_emotion_config(self._config_path)
        self._base_mtime = mtime
        self._cache.clear()

    def _build_profile_config(self, character: str | None) -> tuple[EmotionConfig, list[Path], list[_ConfigSource]]:
        plugin_configs, plugin_paths = self._load_plugin_configs(self._base_config)
        character_config, character_path = self._load_character_config(character)
        overrides = plugin_configs[:]
        if character_config:
            overrides.append(character_config)
        merged = merge_emotion_configs(self._base_config, overrides)
        config_chain = [
            _ConfigSource(
                config=self._base_config, source_path=self._config_path if self._config_path.exists() else None
            )
        ]
        config_chain.extend([_ConfigSource(config=cfg, source_path=path) for cfg, path in plugin_paths])
        if character_config:
            config_chain.append(_ConfigSource(config=character_config, source_path=character_path))

        sources = [source.source_path for source in config_chain if source.source_path]
        sources.extend(self._lexicon_paths_from_chain(config_chain))
        return merged, sources, config_chain

    def _load_plugin_configs(
        self, base_config: EmotionConfig
    ) -> tuple[list[EmotionConfig], list[tuple[EmotionConfig, Path]]]:
        plugin_paths = set(self._plugin_paths)
        plugins_dir = Path(base_config.plugins_dir) if base_config.plugins_dir else self._data_dir / "plugins"
        if plugins_dir.exists():
            plugin_paths.update(plugins_dir.glob(base_config.plugin_glob))
        for entry in base_config.plugins:
            path = Path(entry)
            if not path.is_absolute():
                path = (plugins_dir / path) if plugins_dir.exists() else (self._data_dir / entry)
            if path.is_dir():
                candidate = path / "emotion.yaml"
                if candidate.exists():
                    plugin_paths.add(candidate)
                else:
                    plugin_paths.update(path.glob(base_config.plugin_glob))
            elif path.exists():
                plugin_paths.add(path)

        configs: list[EmotionConfig] = []
        resolved_paths: list[tuple[EmotionConfig, Path]] = []
        for path in sorted(plugin_paths):
            if not path.exists():
                continue
            try:
                config = load_emotion_config(path)
                configs.append(config)
                resolved_paths.append((config, path))
            except Exception as exc:
                logger.warning("Failed to load emotion plugin %s: %s", path, exc)
        return configs, resolved_paths

    def _load_character_config(self, character: str | None) -> tuple[EmotionConfig | None, Path | None]:
        if not character:
            return None, None
        path = self._data_dir / "characters" / f"{character}.yaml"
        if not path.exists():
            return None, None
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            emotion_data = data.get("emotion", {}) if isinstance(data, dict) else {}
            if not emotion_data:
                return None, None
            return emotion_config_from_dict(emotion_data), path
        except Exception as exc:
            logger.warning("Failed to load character emotion config %s: %s", path, exc)
            return None, path

    def _sources_changed(self, cached: _PipelineCache, sources: list[Path]) -> bool:
        cached_paths = set(cached.sources)
        current_paths = set(sources)
        if cached_paths != current_paths:
            return True
        for path in current_paths:
            if not path.exists():
                return True
            mtime = path.stat().st_mtime
            if cached.mtimes.get(path) != mtime:
                return True
        return False

    def _build_pipeline(self, config: EmotionConfig, config_chain: list[_ConfigSource]) -> EmotionPipeline:
        lexicon = self._build_lexicon(config_chain)
        rules = self._build_rules(config, lexicon)
        return EmotionPipeline(rules=rules, bus=self._bus)

    def _build_lexicon(self, config_chain: list[_ConfigSource]) -> EmotionLexicon:
        base = DEFAULT_LEXICON
        merged_keywords = _lexicon_keywords_to_str(base.keywords)
        intensifiers = list(base.intensifiers)
        diminishers = list(base.diminishers)
        negations = list(base.negations)
        positive_hints = list(base.positive_hints)
        negative_hints = list(base.negative_hints)

        for source in config_chain:
            lexicon_config = source.config.lexicon
            if lexicon_config.path:
                lexicon_from_file = self._load_lexicon_file(lexicon_config.path, source.source_path)
                merged_keywords = _merge_keywords(merged_keywords, lexicon_from_file.keywords)
                intensifiers = _merge_list(intensifiers, lexicon_from_file.intensifiers)
                diminishers = _merge_list(diminishers, lexicon_from_file.diminishers)
                negations = _merge_list(negations, lexicon_from_file.negations)
                positive_hints = _merge_list(positive_hints, lexicon_from_file.positive_hints)
                negative_hints = _merge_list(negative_hints, lexicon_from_file.negative_hints)

            merged_keywords = _merge_keywords(merged_keywords, lexicon_config.keywords)
            intensifiers = _merge_list(intensifiers, lexicon_config.intensifiers)
            diminishers = _merge_list(diminishers, lexicon_config.diminishers)
            negations = _merge_list(negations, lexicon_config.negations)
            positive_hints = _merge_list(positive_hints, lexicon_config.positive_hints)
            negative_hints = _merge_list(negative_hints, lexicon_config.negative_hints)

        typed_keywords: dict[EmotionType, list[tuple[str, float]]] = {}
        for emotion_key, entries in merged_keywords.items():
            emotion = _emotion_from_key(emotion_key)
            if not emotion:
                continue
            typed_keywords[emotion] = entries

        return EmotionLexicon(
            keywords=typed_keywords,
            intensifiers=intensifiers,
            diminishers=diminishers,
            negations=negations,
            positive_hints=positive_hints,
            negative_hints=negative_hints,
        )

    def _load_lexicon_file(self, path: str | Path, source_path: Path | None) -> EmotionLexiconConfig:
        path = Path(path)
        if not path.is_absolute():
            if source_path:
                path = source_path.parent / path
            else:
                path = self._data_dir / path
        if not path.exists():
            return EmotionLexiconConfig()
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if "lexicon" in data:
            data = data.get("lexicon", {})
        return lexicon_config_from_dict(data)

    def _lexicon_paths_from_chain(self, config_chain: list[_ConfigSource]) -> list[Path]:
        paths: list[Path] = []
        for source in config_chain:
            lexicon_path = source.config.lexicon.path
            if not lexicon_path:
                continue
            path = Path(lexicon_path)
            if not path.is_absolute():
                if source.source_path:
                    path = source.source_path.parent / path
                else:
                    path = self._data_dir / path
            if path.exists():
                paths.append(path)
        return paths

    def _build_rules(self, config: EmotionConfig, lexicon: EmotionLexicon) -> list:
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


def _lexicon_keywords_to_str(
    keywords: dict[EmotionType, list[tuple[str, float]]],
) -> dict[str, list[tuple[str, float]]]:
    return {emotion.value: list(entries) for emotion, entries in keywords.items()}


def _merge_keywords(
    base: dict[str, list[tuple[str, float]]],
    additions: dict[str, list[tuple[str, float]]],
) -> dict[str, list[tuple[str, float]]]:
    merged = {emotion: list(entries) for emotion, entries in base.items()}
    for emotion, entries in additions.items():
        existing = {keyword.lower(): (keyword, weight) for keyword, weight in merged.get(emotion, [])}
        for keyword, weight in entries:
            existing[keyword.lower()] = (keyword, weight)
        merged[emotion] = list(existing.values())
    return merged


def _merge_list(base: list[str], additions: list[str]) -> list[str]:
    seen = set(base)
    merged = list(base)
    for item in additions:
        if item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _emotion_from_key(key: str) -> EmotionType | None:
    key_lower = str(key).lower()
    for emotion in EmotionType:
        if emotion.value == key_lower or emotion.name.lower() == key_lower:
            return emotion
    return None
