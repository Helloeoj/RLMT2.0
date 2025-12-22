from __future__ import annotations

from typing import List

from catalyst_radar.sources.base import RawEvent


class TickerResolverStub:
    """Phase 1: no external security master.

    Strategy is **TBD**. For now, use whatever tickers are provided in fixture payload.
    """

    def resolve(self, raw: RawEvent) -> List[str]:
        tickers = raw.payload.get("tickers", [])
        if isinstance(tickers, list):
            return [str(t).upper() for t in tickers if str(t).strip()]
        return []
