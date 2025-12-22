from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional, Set

from catalyst_radar.core.models import (
    Confidence,
    CorroborationFields,
    Event,
    EventType,
    FederalAwardFields,
    GeopoliticsFields,
    NotesFields,
    PoliticianDisclosureFields,
    PreOpMilestoneFields,
    SourceType,
)
from catalyst_radar.core.time import parse_utc


class LocalJsonlEventStore:
    """Append-only Event Ledger stored as JSONL.

    Phase 0 requires dedupe/versioning. This store supports:
    - append-only persistence
    - simple indices for event_id and source_hash to enable dedupe

    Versioning semantics are TBD in Phase 1.
    """

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")
        self._by_id: Dict[str, Event] = {}
        self._hashes: Set[str] = set()
        self._load_existing()

    def _load_existing(self) -> None:
        text = self._path.read_text(encoding="utf-8")
        if not text.strip():
            return
        for line in text.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            ev = _event_from_dict(obj)
            self._by_id[ev.event_id] = ev
            self._hashes.add(ev.source_hash)

    def has_source_hash(self, source_hash: str) -> bool:
        return source_hash in self._hashes

    def append(self, event: Event) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self._by_id[event.event_id] = event
        self._hashes.add(event.source_hash)

    def get(self, event_id: str) -> Optional[Event]:
        return self._by_id.get(event_id)

    def iter_all(self) -> Iterable[Event]:
        return list(self._by_id.values())


def _maybe_dc(value, cls):
    if value is None:
        return None
    if isinstance(value, cls):
        return value
    if isinstance(value, dict):
        return cls(**value)
    return None


def _event_from_dict(d: dict) -> Event:
    return Event(
        event_id=str(d["event_id"]),
        event_type=EventType(d["event_type"]),
        title=str(d["title"]),
        summary=str(d["summary"]),
        event_timestamp_utc=parse_utc(d["event_timestamp_utc"]),
        discovered_timestamp_utc=parse_utc(d["discovered_timestamp_utc"]),
        source_type=SourceType(d["source_type"]),
        source_name=str(d["source_name"]),
        source_url=str(d["source_url"]),
        source_hash=str(d["source_hash"]),
        entities=list(d.get("entities") or []),
        tickers=list(d.get("tickers") or []),
        theme_tags=list(d.get("theme_tags") or []),
        confidence=Confidence(d.get("confidence")),
        confidence_rationale=str(d.get("confidence_rationale") or "TBD"),
        credibility_score=int(d.get("credibility_score", 0)),
        freshness_score=int(d.get("freshness_score", 0)),
        materiality_score=int(d.get("materiality_score", 0)),
        overall_score=int(d.get("overall_score", 0)),
        politician_disclosure=_maybe_dc(d.get("politician_disclosure"), PoliticianDisclosureFields),
        federal_award=_maybe_dc(d.get("federal_award"), FederalAwardFields),
        geopolitics=_maybe_dc(d.get("geopolitics"), GeopoliticsFields),
        preop_milestone=_maybe_dc(d.get("preop_milestone"), PreOpMilestoneFields),
        corroboration=_maybe_dc(d.get("corroboration"), CorroborationFields),
        notes=_maybe_dc(d.get("notes"), NotesFields),
    )
