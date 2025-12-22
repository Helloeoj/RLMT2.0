from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from catalyst_radar.core.models import Event, WatchlistEntry


def write_watchlist(path: str | Path, *, generated_at_utc: datetime, message: str, entries: List[WatchlistEntry], digest_events: List[Event]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    obj: Dict[str, Any] = {
        "generated_at_utc": generated_at_utc.astimezone(timezone.utc).isoformat(),
        "message": message,
        "watchlist": [e.to_dict() for e in entries],
        "digest": [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type.value,
                "title": ev.title,
                "event_timestamp_utc": ev.event_timestamp_utc.astimezone(timezone.utc).isoformat(),
                "source_url": ev.source_url,
                "tickers": ev.tickers,
                "confidence": ev.confidence.value,
            }
            for ev in sorted(digest_events, key=lambda x: x.discovered_timestamp_utc, reverse=True)[:25]
        ],
    }

    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
