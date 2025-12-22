from __future__ import annotations

from dataclasses import asdict

from ..core.models import Event, WatchlistEntry


def event_to_json(e: Event) -> dict:
    d = asdict(e)
    d["event_timestamp_utc"] = e.event_timestamp_utc.isoformat()
    d["discovered_timestamp_utc"] = e.discovered_timestamp_utc.isoformat()
    d["event_type"] = e.event_type.value
    d["source_type"] = e.source_type.value
    d["confidence"] = e.confidence.value
    return d


def watchlist_entry_to_json(w: WatchlistEntry) -> dict:
    d = asdict(w)
    d["confidence"] = w.confidence.value
    return d
