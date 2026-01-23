"""
Emotion configuration loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...config.file_utils import load_config_data, resolve_config_path
from ...config.loader import get_data_dir
from .config_models import EmotionConfig
from .config_utils import emotion_config_from_dict


def load_emotion_config(path: str | Path | None = None) -> EmotionConfig:
    """Load emotion config from yaml or toml."""
    if path is None:
        path = Path(get_data_dir()) / "emotion.yaml"
    path = resolve_config_path(Path(path))
    data: dict[str, Any] = load_config_data(path)
    return emotion_config_from_dict(data)
