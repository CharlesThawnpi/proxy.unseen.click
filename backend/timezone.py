"""Project-wide Myanmar Time helpers.

Business/customer dates use Myanmar Time (MMT, UTC+06:30, Asia/Yangon). External UTC
timestamps should be converted at the boundary before customer/product use. New code should
avoid naive datetimes; `to_mmt` rejects them so callers must label the source timezone.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

MMT_TZ_NAME = "Asia/Yangon"
MMT_ABBR = "MMT"
MMT_OFFSET = "UTC+06:30"
MMT = ZoneInfo(MMT_TZ_NAME)


def now_mmt() -> datetime:
    """Current timezone-aware Myanmar Time."""
    return datetime.now(MMT)


def to_mmt(dt: datetime) -> datetime:
    """Convert an aware datetime to Myanmar Time.

    Naive datetimes are rejected because guessing their source timezone can shift subscription,
    payment, invoice, and customer-visible dates.
    """
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("to_mmt requires a timezone-aware datetime")
    return dt.astimezone(MMT)


def format_mmt(dt: datetime, *, include_tz_name: bool = False) -> str:
    """Format an aware datetime as a customer/business-safe MMT string."""
    converted = to_mmt(dt)
    label = f"{MMT_ABBR} ({MMT_TZ_NAME})" if include_tz_name else MMT_ABBR
    return f"{converted:%Y-%m-%d %H:%M:%S} {label}"


def today_mmt() -> date:
    """Current Myanmar calendar date."""
    return now_mmt().date()


def parse_mmt(value: str) -> datetime:
    """Parse an ISO-like local Myanmar Time string and attach Asia/Yangon.

    This is for operator/test inputs such as `2026-06-16 09:00:00`; it should not be
    used to silently reinterpret external UTC timestamps.
    """
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=MMT)
    return to_mmt(parsed)


def storage_mmt(dt: datetime) -> str:
    """Canonical app-created business timestamp string for future DB writes."""
    return to_mmt(dt).isoformat(timespec="seconds")

