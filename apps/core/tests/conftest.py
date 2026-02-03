"""Pytest sandbox helpers.

This repo runs in environments where:
- Writes outside the workspace are restricted (system temp is not usable).
- Deleting files/directories may be denied.

To keep tests deterministic and non-flaky, we:
- Force `tempfile` to use a workspace-local directory.
- Wrap `tempfile.TemporaryDirectory` to ignore cleanup errors.
- Provide our own `tmp_path` fixture (pytest's tmpdir plugin is disabled).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BASE_TMP = _REPO_ROOT / ".tmp" / "pytest_sandbox"
_BASE_TMP.mkdir(parents=True, exist_ok=True)

# Ensure stdlib tempfile uses workspace temp.
os.environ.setdefault("TMPDIR", str(_BASE_TMP))
os.environ.setdefault("TEMP", str(_BASE_TMP))
os.environ.setdefault("TMP", str(_BASE_TMP))
tempfile.tempdir = str(_BASE_TMP)


class _WorkspaceTemporaryDirectory:  # noqa: D101
    def __init__(self, *args, **kwargs):  # noqa: ANN001,ANN002
        base = Path(kwargs.get("dir") or _BASE_TMP)
        prefix = str(kwargs.get("prefix") or "tmp")
        suffix = str(kwargs.get("suffix") or "")
        self._path = base / f"{prefix}{uuid4().hex}{suffix}"
        self._path.mkdir(parents=True, exist_ok=False)
        self.name = str(self._path)

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    def cleanup(self) -> None:
        # Deletion may be denied in sandboxed environments; best-effort cleanup is not required for tests.
        return None


tempfile.TemporaryDirectory = _WorkspaceTemporaryDirectory  # type: ignore[assignment]


@pytest.fixture
def tmp_path() -> Path:
    """Workspace-local replacement for pytest's tmp_path fixture."""

    path = _BASE_TMP / f"case-{uuid4()}"
    path.mkdir(parents=True, exist_ok=True)
    return path
