from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, Iterable, List

from catalyst_radar.config.settings import Settings
from catalyst_radar.core.models import Confidence, Event, WatchlistEntry
from catalyst_radar.watchlist.compliance_gate import is_event_eligible_for_watchlist


_CONF_ORDER = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def _max_conf(conf_list: List[Confidence]) -> Confidence:
    return max(conf_list, key=lambda c: _CONF_ORDER[c])


class WatchlistBuilder:
    def build(self, events: Iterable[Event], *, now_utc: datetime, settings: Settings) -> List[WatchlistEntry]:
        per_ticker: Dict[str, List[Event]] = defaultdict(list)
        for e in events:
            if not is_event_eligible_for_watchlist(e, now_utc=now_utc, settings=settings):
                continue
            for t in e.tickers:
                per_ticker[t].append(e)

        entries: List[WatchlistEntry] = []
        for ticker, evs in per_ticker.items():
            evs_sorted = sorted(evs, key=lambda x: (x.overall_score, x.event_timestamp_utc), reverse=True)
            top = evs_sorted[:3]

            # Placeholder aggregation (no scoring formula defined in Phase 0)
            rank_score = int(max((e.overall_score for e in top), default=0))
            comp_scores = {
                "Freshness": int(max((e.freshness_score for e in top), default=0)),
                "Materiality": int(max((e.materiality_score for e in top), default=0)),
                "Source Credibility": int(max((e.credibility_score for e in top), default=0)),
                "Theme Fit": 0,       # TBD (Phase 0 defines component but no formula)
                "De-risking": 0,      # TBD (Phase 0 defines component but no formula)
            }

            conf = _max_conf([e.confidence for e in top])
            conf_reason = "Derived from supporting Events (scoring formulas TBD)."

            company_name = (top[0].entities[0] if top and top[0].entities else "TBD")
            time_horizon = "TBD"  # Phase 0 requires a horizon tag but no mapping rules yet.

            entries.append(
                WatchlistEntry(
                    ticker=ticker,
                    company_name=company_name,
                    rank_score=rank_score,
                    component_scores=comp_scores,
                    top_events=[e.event_id for e in top],
                    confidence=conf,
                    confidence_reason=conf_reason,
                    time_horizon=time_horizon,
                )
            )

        # Sort descending by rank_score (ties: alphabetical)
        return sorted(entries, key=lambda w: (w.rank_score, w.ticker), reverse=True)
