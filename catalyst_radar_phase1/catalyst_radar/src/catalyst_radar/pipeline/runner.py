from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from catalyst_radar.config.logging import get_logger
from catalyst_radar.config.settings import Settings
from catalyst_radar.core.schema_validation import validate_event
from catalyst_radar.core.time import utc_now
from catalyst_radar.dedupe.deduplicator import Deduplicator
from catalyst_radar.dedupe.fingerprint import Fingerprinter
from catalyst_radar.normalize.normalizer import CanonicalEventNormalizer
from catalyst_radar.output.writer import write_watchlist
from catalyst_radar.scoring.base import ScoringEngine
from catalyst_radar.sources.base import RawEvent
from catalyst_radar.sources.stubs.politician_disclosure_stub import PoliticianDisclosureStub
from catalyst_radar.sources.stubs.federal_award_stub import FederalAwardStub
from catalyst_radar.sources.stubs.geopolitics_news_stub import GeopoliticsNewsStub
from catalyst_radar.sources.stubs.energy_resources_stub import EnergyResourcesStub
from catalyst_radar.sources.stubs.preop_milestone_stub import PreOpMilestoneStub
from catalyst_radar.storage.local_jsonl_store import LocalJsonlEventStore
from catalyst_radar.watchlist.builder import WatchlistBuilder


logger = get_logger(__name__)


@dataclass
class PipelineResult:
    events_seen: int
    events_new: int
    watchlist_count: int
    ledger_path: str
    watchlist_path: str


class PipelineRunner:
    def __init__(self, *, settings: Settings, fixtures_path: str) -> None:
        self.settings = settings
        self.fixtures_path = fixtures_path

    def run(self, *, since_utc: Optional[datetime] = None) -> PipelineResult:
        now = utc_now()
        store = LocalJsonlEventStore(self.settings.ledger_path)
        deduper = Deduplicator(store)
        fingerprinter = Fingerprinter()
        normalizer = CanonicalEventNormalizer(fingerprinter=fingerprinter)
        scorer = ScoringEngine()
        watchlist_builder = WatchlistBuilder()

        sources = [
            PoliticianDisclosureStub(self.fixtures_path),
            FederalAwardStub(self.fixtures_path),
            GeopoliticsNewsStub(self.fixtures_path),
            EnergyResourcesStub(self.fixtures_path),
            PreOpMilestoneStub(self.fixtures_path),
        ]

        raw_events: List[RawEvent] = []
        for s in sources:
            fetched = s.fetch(since_utc=since_utc)
            logger.info("source=%s fetched=%d", s.name, len(fetched))
            raw_events.extend(fetched)

        events_new = 0
        for raw in raw_events:
            ev = normalizer.normalize(raw)
            ev = scorer.score(ev, now_utc=now)
            validate_event(ev)

            ev, is_new = deduper.apply(ev)
            if is_new:
                store.append(ev)
                events_new += 1

        all_events = list(store.iter_all())
        watchlist_entries = watchlist_builder.build(all_events, now_utc=now, settings=self.settings)

        out_dir = Path(self.settings.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        watchlist_path = out_dir / "watchlist.json"

        if watchlist_entries:
            msg = "Ranked watchlist (Phase 1 skeleton; scoring formulas TBD)."
        else:
            # Phase 0 "do nothing" condition
            msg = "No actionable catalysts detected"

        write_watchlist(
            watchlist_path,
            generated_at_utc=now,
            message=msg,
            entries=watchlist_entries,
            digest_events=all_events,
        )

        logger.info(
            "pipeline_done events_seen=%d events_new=%d watchlist=%d",
            len(raw_events),
            events_new,
            len(watchlist_entries),
        )

        return PipelineResult(
            events_seen=len(raw_events),
            events_new=events_new,
            watchlist_count=len(watchlist_entries),
            ledger_path=str(self.settings.ledger_path),
            watchlist_path=str(watchlist_path),
        )
