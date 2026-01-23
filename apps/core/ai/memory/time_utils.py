"""Shared time helpers for memory module."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, tzinfo

logger = logging.getLogger(__name__)

_DEFAULT_TIMEZONE: tzinfo = UTC


def _system_timezone() -> tzinfo:
    tz = datetime.now().astimezone().tzinfo
    return tz or UTC


def resolve_timezone(name: str | None) -> tzinfo:
    if not name:
        return UTC
    lowered = name.strip().lower()
    if lowered in {"utc", "utc+0", "utc+00:00"}:
        return UTC
    if lowered in {"local", "system"}:
        return _system_timezone()
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        logger.warning("Invalid timezone '%s', using UTC", name)
        return UTC


def set_default_timezone(name: str | None) -> tzinfo:
    global _DEFAULT_TIMEZONE
    _DEFAULT_TIMEZONE = resolve_timezone(name)
    return _DEFAULT_TIMEZONE


def get_default_timezone() -> tzinfo:
    return _DEFAULT_TIMEZONE


def now(tz: tzinfo | None = None) -> datetime:
    return datetime.now(tz or _DEFAULT_TIMEZONE)


def now_timestamp(tz: tzinfo | None = None) -> float:
    return now(tz).timestamp()


def ensure_timezone(value: datetime, tz: tzinfo | None = None) -> datetime:
    target = tz or _DEFAULT_TIMEZONE
    if value.tzinfo is None:
        return value.replace(tzinfo=target)
    return value.astimezone(target)


def from_timestamp(value: float, tz: tzinfo | None = None) -> datetime:
    return datetime.fromtimestamp(float(value), tz=tz or _DEFAULT_TIMEZONE)


def format_timestamp(value: datetime, fmt: str, tz: tzinfo | None = None) -> str:
    return ensure_timezone(value, tz).strftime(fmt)
