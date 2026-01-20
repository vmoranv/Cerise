"""
Lexicon helpers for emotion manager.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .config_models import EmotionLexiconConfig
from .config_utils import lexicon_config_from_dict
from .lexicon import DEFAULT_LEXICON, EmotionLexicon
from .manager_types import _ConfigSource
from .types import EmotionType


class LexiconMixin:
    _data_dir: Path

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
