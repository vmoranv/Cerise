"""Config bootstrap helpers."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .paths import ensure_data_dir, get_data_dir

_TEMPLATE_TARGETS: dict[str, str] = {
    "config.yaml": "config.yaml",
    "providers.yaml": "providers.yaml",
    "mcp.yaml": "mcp.yaml",
    "memory.yaml": "memory.yaml",
    "emotion.yaml": "emotion.yaml",
    "proactive.yaml": "proactive.yaml",
    "character.yaml": "characters/default.yaml",
}


@dataclass
class BootstrapReport:
    """Result summary for config bootstrap."""

    data_dir: Path
    created: list[Path] = field(default_factory=list)
    overwritten: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def bootstrap_data_dir(data_dir: Path | None = None, overwrite: bool = False) -> BootstrapReport:
    """Copy template configs into data dir.

    Args:
        data_dir: Target data directory. Defaults to ``get_data_dir()``.
        overwrite: Overwrite existing files when True.
    """
    target_dir = ensure_data_dir(data_dir or get_data_dir())
    examples_dir = Path(__file__).resolve().parent / "examples"
    report = BootstrapReport(data_dir=target_dir)

    for template_name, relative_target in _TEMPLATE_TARGETS.items():
        source = examples_dir / template_name
        if not source.exists():
            raise FileNotFoundError(f"Missing config template: {source}")

        destination = target_dir / relative_target
        destination.parent.mkdir(parents=True, exist_ok=True)

        existed_before = destination.exists()
        if existed_before and not overwrite:
            report.skipped.append(destination)
            continue

        shutil.copyfile(source, destination)
        if existed_before:
            report.overwritten.append(destination)
        else:
            report.created.append(destination)

    return report
