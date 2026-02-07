"""
Cerise Core entrypoint.

Examples:
  uv run cerise
  uv run cerise run --host 127.0.0.1 --port 8001
  uv run cerise init-config
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path for `python apps/core/main.py`.
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from apps.core.api import create_app  # noqa: E402
from apps.core.config import AppConfig, get_config_loader  # noqa: E402
from apps.core.config.bootstrap import bootstrap_data_dir  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = create_app()


@dataclass(frozen=True)
class ServerRunOptions:
    host: str
    port: int
    reload: bool
    log_level: str


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_port(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        port = int(value)
    except ValueError:
        return None
    if not (1 <= port <= 65535):
        return None
    return port


def _load_app_config() -> AppConfig:
    try:
        return get_config_loader().get_app_config()
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Failed to load app config for startup options: %s", exc)
        return AppConfig()


def resolve_run_options(args: argparse.Namespace) -> ServerRunOptions:
    app_config = _load_app_config()

    host = args.host or _env_first("CERISE_SERVER_HOST", "CERISE_HOST") or app_config.server.host

    port = args.port
    if port is None:
        port = _parse_port(_env_first("CERISE_SERVER_PORT", "CERISE_PORT"))
    if port is None:
        port = app_config.server.port

    reload_override = args.reload
    if reload_override is None:
        reload_override = _parse_bool(_env_first("CERISE_SERVER_DEBUG", "CERISE_RELOAD"))
    if reload_override is None:
        reload_override = bool(app_config.server.debug)

    log_level = args.log_level or _env_first("CERISE_LOG_LEVEL") or app_config.logging.level

    return ServerRunOptions(
        host=host,
        port=port,
        reload=reload_override,
        log_level=log_level.lower(),
    )


def run_server(options: ServerRunOptions) -> None:
    import uvicorn

    uvicorn.run(
        "apps.core.main:app",
        host=options.host,
        port=options.port,
        reload=options.reload,
        log_level=options.log_level,
    )


def init_config(data_dir: Path | None = None, force: bool = False) -> int:
    report = bootstrap_data_dir(data_dir=data_dir, overwrite=force)
    print(f"Config data dir: {report.data_dir}")
    if report.created:
        print("Created:")
        for path in report.created:
            print(f"  - {path}")
    if report.overwritten:
        print("Overwritten:")
        for path in report.overwritten:
            print(f"  - {path}")
    if report.skipped:
        print("Skipped (already exists):")
        for path in report.skipped:
            print(f"  - {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cerise core service")
    parser.set_defaults(command="run", host=None, port=None, log_level=None, reload=None)
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run API server")
    run_parser.add_argument("--host", type=str, default=None, help="Bind host")
    run_parser.add_argument("--port", type=int, default=None, help="Bind port")
    run_parser.add_argument("--log-level", type=str, default=None, help="Uvicorn log level")
    run_parser.set_defaults(reload=None)
    run_parser.add_argument("--reload", dest="reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")

    init_parser = subparsers.add_parser("init-config", help="Initialize config files from templates")
    init_parser.add_argument("--data-dir", type=Path, default=None, help="Target config data directory")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        return init_config(data_dir=args.data_dir, force=args.force)

    # Default command = run.
    options = resolve_run_options(args)
    run_server(options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
