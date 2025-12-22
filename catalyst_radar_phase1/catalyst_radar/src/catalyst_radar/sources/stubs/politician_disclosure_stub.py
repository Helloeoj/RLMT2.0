from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from catalyst_radar.core.models import EventType
from catalyst_radar.sources.base import RawEvent, SourceAdapter
from catalyst_radar.sources.fixtures_loader import load_fixture_raw_events


class PoliticianDisclosureStub(SourceAdapter):
    name = "politician_disclosure_stub"

    def __init__(self, fixture_path: str) -> None:
        self._fixture_path = fixture_path

    def fetch(self, *, since_utc: Optional[datetime] = None) -> List[RawEvent]:
        events = load_fixture_raw_events(self._fixture_path)
        out: List[RawEvent] = []
        for e in events:
            et = e.payload.get("event_type")
            if et == EventType.POLITICIAN_DISCLOSURE.value:
                if since_utc is None or e.discovered_timestamp_utc >= since_utc:
                    out.append(e)
        return out
