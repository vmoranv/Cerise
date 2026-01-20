"""
Emotion configuration loader.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ...config.loader import get_data_dir
from .config_models import EmotionConfig
from .config_utils import emotion_config_from_dict


def load_emotion_config(path: str | Path | None = None) -> EmotionConfig:
    """Load emotion config from yaml."""
    if path is None:
        path = Path(get_data_dir()) / "emotion.yaml"
    path = Path(path)
    data: dict[str, Any] = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    return emotion_config_from_dict(data)
