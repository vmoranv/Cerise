"""
Config paths helpers.
"""

import os
from pathlib import Path


def get_data_dir() -> Path:
    """Get the Cerise data directory (~/.cerise/)."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("USERPROFILE", "~"))
    else:
        base = Path.home()

    return base / ".cerise"


def ensure_data_dir() -> Path:
    """Ensure data directory exists with default structure."""
    data_dir = get_data_dir()

    dirs = [
        data_dir,
        data_dir / "plugins",
        data_dir / "characters",
        data_dir / "logs",
        data_dir / "cache",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    return data_dir
