from __future__ import annotations

import hashlib

from catalyst_radar.sources.base import RawEvent


class Fingerprinter:
    """Compute Phase 0 `source_hash / fingerprint` for deduplication."""

    def fingerprint(self, raw: RawEvent) -> str:
        # Conservative: depend only on public URL + canonical event timestamp + title if present.
        p = raw.payload or {}
        title = str(p.get("title", "")).strip()
        event_ts = str(p.get("event_timestamp_utc", "")).strip()
        material = f"{raw.source_url}|{event_ts}|{title}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()
