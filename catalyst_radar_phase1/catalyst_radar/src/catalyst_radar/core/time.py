from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(dt_str: str) -> datetime:
    """Parse an ISO-8601 datetime string.

    The fixtures use ISO strings with timezone offsets.
    """
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        # Treat naive as UTC (Phase 1 fixtures should include tz, but keep safe).
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
