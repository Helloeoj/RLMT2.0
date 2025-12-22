from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..base import RawEvent
from ..fixtures_loader import load_fixture_events
from ...core.models import SourceType
from ...core.time import parse_utc_iso


class FixtureSourceAdapter:
    """Stub adapter that reads RawEvents from a local JSON fixture file."""

    def __init__(self, *, name: str, fixture_path: str):
        self.name = name
        self._fixture_path = fixture_path

    def fetch(self, *, since_utc: Optional[datetime] = None) -> list[RawEvent]:
        rows = load_fixture_events(self._fixture_path)
        out: list[RawEvent] = []
        for r in rows:
            # Each row is a RawEvent-like dict.
            discovered = parse_utc_iso(r["discovered_timestamp_utc"])
            if since_utc is not None and discovered < since_utc:
                continue
            out.append(
                RawEvent(
                    source_name=r["source_name"],
                    source_url=r["source_url"],
                    source_type=SourceType(r["source_type"]),
                    discovered_timestamp_utc=discovered,
                    payload=r["payload"],
                )
            )
        return out
