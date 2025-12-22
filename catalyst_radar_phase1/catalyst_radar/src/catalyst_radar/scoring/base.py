from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from catalyst_radar.core.models import Event


class ScoringEngine:
    """Phase 1 scoring scaffold.

    Phase 0 defines the score fields but does not define numeric formulas.
    This engine therefore defaults to leaving fixture-provided scores unchanged.
    """

    def score(self, event: Event, *, now_utc: datetime) -> Event:
        # No-op by default; keep canonical required fields.
        return event
