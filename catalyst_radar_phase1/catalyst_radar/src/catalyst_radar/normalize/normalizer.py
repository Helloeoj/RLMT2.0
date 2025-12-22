from __future__ import annotations

from typing import Any, Dict, Optional

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
)
from catalyst_radar.core.time import parse_utc
from catalyst_radar.dedupe.fingerprint import Fingerprinter
from catalyst_radar.sources.base import RawEvent
from .ticker_resolver import TickerResolverStub


class CanonicalEventNormalizer:
    """RawEvent -> Event mapping contract.

    Phase 1 uses fixture payloads that already resemble the canonical schema.
    """

    def __init__(self, *, fingerprinter: Fingerprinter, ticker_resolver: Optional[TickerResolverStub] = None) -> None:
        self._fingerprinter = fingerprinter
        self._ticker_resolver = ticker_resolver or TickerResolverStub()

    def normalize(self, raw: RawEvent) -> Event:
        p: Dict[str, Any] = dict(raw.payload or {})

        # Required base fields (Phase 0)
        event_type = EventType(p["event_type"])
        title = str(p["title"])
        summary = str(p["summary"])
        event_ts = parse_utc(p["event_timestamp_utc"])

        source_hash = self._fingerprinter.fingerprint(raw)
        event_id = str(p.get("event_id") or source_hash)

        entities = list(p.get("entities") or [])
        theme_tags = list(p.get("theme_tags") or [])

        tickers = self._ticker_resolver.resolve(raw)

        confidence = Confidence(str(p.get("confidence", "LOW")).upper())
        confidence_rationale = str(p.get("confidence_rationale", "TBD"))

        # Scores (Phase 0 required). Formulas/thresholds are TBD in Phase 1.
        credibility_score = int(p.get("credibility_score", 0))
        freshness_score = int(p.get("freshness_score", 0))
        materiality_score = int(p.get("materiality_score", 0))
        overall_score = int(p.get("overall_score", 0))

        # Optional per-type blocks
        politician_disclosure = _maybe_dataclass(p.get("politician_disclosure"), PoliticianDisclosureFields)
        federal_award = _maybe_dataclass(p.get("federal_award"), FederalAwardFields)
        geopolitics = _maybe_dataclass(p.get("geopolitics"), GeopoliticsFields)
        preop_milestone = _maybe_dataclass(p.get("preop_milestone"), PreOpMilestoneFields)
        corroboration = _maybe_dataclass(p.get("corroboration"), CorroborationFields)
        notes = _maybe_dataclass(p.get("notes"), NotesFields)

        return Event(
            event_id=event_id,
            event_type=event_type,
            title=title,
            summary=summary,
            event_timestamp_utc=event_ts,
            discovered_timestamp_utc=raw.discovered_timestamp_utc,
            source_type=raw.source_type,
            source_name=raw.source_name,
            source_url=raw.source_url,
            source_hash=source_hash,
            entities=entities,
            tickers=tickers,
            theme_tags=theme_tags,
            confidence=confidence,
            confidence_rationale=confidence_rationale,
            credibility_score=credibility_score,
            freshness_score=freshness_score,
            materiality_score=materiality_score,
            overall_score=overall_score,
            politician_disclosure=politician_disclosure,
            federal_award=federal_award,
            geopolitics=geopolitics,
            preop_milestone=preop_milestone,
            corroboration=corroboration,
            notes=notes,
        )


def _maybe_dataclass(value: Any, cls):
    if value is None:
        return None
    if isinstance(value, cls):
        return value
    if isinstance(value, dict):
        return cls(**value)
    return None
