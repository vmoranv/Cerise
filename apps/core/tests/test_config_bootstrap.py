"""Tests for config bootstrap helpers."""

from pathlib import Path

from apps.core.config.bootstrap import bootstrap_data_dir


def _relative_set(paths: list[Path], base: Path) -> set[str]:
    return {path.relative_to(base).as_posix() for path in paths}


def test_bootstrap_creates_expected_templates(tmp_path: Path) -> None:
    report = bootstrap_data_dir(data_dir=tmp_path)

    assert _relative_set(report.created, tmp_path) == {
        "config.yaml",
        "providers.yaml",
        "mcp.yaml",
        "memory.yaml",
        "emotion.yaml",
        "proactive.yaml",
        "characters/default.yaml",
    }
    assert report.overwritten == []
    assert report.skipped == []


def test_bootstrap_respects_overwrite_flag(tmp_path: Path) -> None:
    bootstrap_data_dir(data_dir=tmp_path)

    config_file = tmp_path / "config.yaml"
    config_file.write_text("server:\n  port: 9001\n", encoding="utf-8")

    report_no_overwrite = bootstrap_data_dir(data_dir=tmp_path, overwrite=False)
    assert config_file in report_no_overwrite.skipped
    assert config_file.read_text(encoding="utf-8") == "server:\n  port: 9001\n"

    report_overwrite = bootstrap_data_dir(data_dir=tmp_path, overwrite=True)
    assert config_file in report_overwrite.overwritten

    template = Path(__file__).resolve().parent.parent / "config" / "examples" / "config.yaml"
    assert config_file.read_text(encoding="utf-8") == template.read_text(encoding="utf-8")
