from __future__ import annotations

import json
from pathlib import Path
from typing import List

from catalyst_radar.core.time import parse_utc
from catalyst_radar.core.models import SourceType
from .base import RawEvent


def load_fixture_raw_events(path: str | Path) -> List[RawEvent]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    out: List[RawEvent] = []
    for item in data:
        out.append(
            RawEvent(
                source_name=item["source_name"],
                source_url=item["source_url"],
                source_type=SourceType(item["source_type"]),
                discovered_timestamp_utc=parse_utc(item["discovered_timestamp_utc"]),
                payload=item.get("payload", {}),
            )
        )
    return out
