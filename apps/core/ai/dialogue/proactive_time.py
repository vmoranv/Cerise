"""Time helpers for proactive chat."""

from __future__ import annotations

from datetime import datetime, timedelta


def parse_quiet_hours(value: str) -> tuple[int, int] | None:
    if not value or not isinstance(value, str):
        return None
    parts = value.split("-")
    if len(parts) != 2:
        return None
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        return None
    if not (0 <= start <= 23 and 0 <= end <= 23):
        return None
    return start, end


def is_quiet_time(now: datetime, start_hour: int, end_hour: int) -> bool:
    if start_hour == end_hour:
        return False
    hour = now.hour
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def next_quiet_end(now: datetime, start_hour: int, end_hour: int) -> datetime:
    if start_hour < end_hour:
        end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        if end <= now:
            end += timedelta(days=1)
        return end
    if now.hour >= start_hour:
        end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return end
    end = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    if end <= now:
        end += timedelta(days=1)
    return end
