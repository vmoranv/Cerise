"""
Config paths helpers.
"""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Get the Cerise data directory, honoring CERISE_DATA_DIR when set."""
    env_override = os.environ.get("CERISE_DATA_DIR")
    if env_override:
        return Path(env_override).expanduser()

    if os.name == "nt":  # Windows
        base = Path(os.environ.get("USERPROFILE", "~"))
    else:
        base = Path.home()

    return base / ".cerise"


def ensure_data_dir(data_dir: Path | None = None) -> Path:
    """Ensure data directory exists with default structure."""
    data_dir = data_dir or get_data_dir()

    dirs = [
        data_dir,
        data_dir / "plugins",
        data_dir / "characters",
        data_dir / "logs",
        data_dir / "cache",
        data_dir / "stars",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    return data_dir
