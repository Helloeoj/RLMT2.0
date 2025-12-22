from __future__ import annotations

from datetime import datetime

from catalyst_radar.config.settings import Settings
from catalyst_radar.core.models import Confidence, Event, EventType


_CONF_ORDER = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


def confidence_meets_min(conf: Confidence, min_conf: Confidence) -> bool:
    return _CONF_ORDER[conf] >= _CONF_ORDER[min_conf]


def is_event_stale(event: Event, *, now_utc: datetime, settings: Settings) -> bool:
    age_days = (now_utc - event.event_timestamp_utc).days
    if event.event_type == EventType.POLITICIAN_DISCLOSURE:
        return age_days > settings.disclosure_stale_days
    # Phase 0 example: >30 days for news-like events
    return age_days > settings.news_stale_days


def is_event_eligible_for_watchlist(event: Event, *, now_utc: datetime, settings: Settings) -> bool:
    """Apply Phase 0 safety gates for watchlist promotion.

    - If ticker mapping uncertain (no tickers) -> can be logged but cannot promote.
    - Require minimum confidence for a ticker to appear (default Medium+).
    - Stale events beyond window -> excluded.
    - Credibility threshold is only enforced if user config sets it (default is TBD).
    """
    if not event.tickers:
        return False

    if not confidence_meets_min(event.confidence, settings.min_confidence):
        return False

    if is_event_stale(event, now_utc=now_utc, settings=settings):
        return False

    if settings.min_credibility is not None:
        if event.credibility_score < settings.min_credibility:
            return False

    return True
