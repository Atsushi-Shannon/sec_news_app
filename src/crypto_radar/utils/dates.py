from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from time import struct_time


def now_utc() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def datetime_from_struct(value: struct_time | None) -> datetime | None:
    if value is None:
        return None
    return datetime(*value[:6], tzinfo=UTC)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = parsedate_to_datetime(text)
        return ensure_utc(parsed)
    except (TypeError, ValueError):
        pass

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return ensure_utc(parsed)
    except ValueError:
        return None


def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat().replace("+00:00", "Z")


def is_recent(value: datetime | None, *, now: datetime, within_hours: int) -> bool:
    if value is None:
        return False
    published = ensure_utc(value)
    return timedelta(0) <= ensure_utc(now) - published <= timedelta(hours=within_hours)
