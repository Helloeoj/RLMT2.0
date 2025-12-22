from __future__ import annotations

from typing import Tuple

from catalyst_radar.core.models import Event
from catalyst_radar.storage.base import EventStore


class Deduplicator:
    """Detect exact duplicates using Phase 0 `source_hash / fingerprint`.

    Phase 0 also mentions versioning. Versioning rules are **TBD** in Phase 1;
    this implementation only suppresses exact duplicates.
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store

    def apply(self, event: Event) -> Tuple[Event, bool]:
        if hasattr(self._store, "has_source_hash") and self._store.has_source_hash(event.source_hash):
            return event, False
        # If store can fetch by event_id and it exists, treat as not-new (conservative)
        existing = self._store.get(event.event_id)
        if existing is not None:
            return event, False
        return event, True
