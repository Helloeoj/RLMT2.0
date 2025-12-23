from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..connector_base import Connector
from ..http_client import HttpClient, HttpConfig
from ..models import RawRecord, Checkpoint
from ..utils import now_utc


class UsaSpendingAwardsConnector(Connector):
    @property
    def name(self) -> str:
        return "usaspending_awards"

    def __init__(self, user_agent: str, agency_name: str | None = None, agency_tier: str = "toptier", agency_type: str = "awarding"):
        self.client = HttpClient(HttpConfig(user_agent=user_agent))
        self.agency_name = agency_name
        self.agency_tier = agency_tier
        self.agency_type = agency_type

    def fetch_batch(self, checkpoint: Checkpoint, limit: int) -> tuple[list[RawRecord], Checkpoint]:
        # Config-driven; stores raw JSON response.
        endpoint = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

        safety_delta = timedelta(hours=6)
        end = now_utc()
        since = checkpoint.last_since_utc or (end - timedelta(days=1))
        window_start = since - safety_delta

        page = int(checkpoint.last_cursor or "1")

        filters: dict[str, Any] = {
            "time_period": [{
                "date_type": "action_date",
                "start_date": window_start.date().isoformat(),
                "end_date": end.date().isoformat(),
            }]
        }

        if self.agency_name:
            filters["agencies"] = [{
                "type": self.agency_type,
                "tier": self.agency_tier,
                "name": self.agency_name,
            }]

        body: dict[str, Any] = {
            "filters": filters,
            "limit": min(max(limit, 1), 1000),
            "page": page,
            "sort": "Award Amount",
            "order": "desc",
            "subawards": False,
        }

        resp = self.client.request("POST", endpoint, json=body, headers={"Content-Type": "application/json"})

        record_id = f"{window_start.date().isoformat()}:{end.date().isoformat()}:page={page}"
        rec = RawRecord(
            source_type="usaspending",
            source_name="spending_by_award",
            url=endpoint,
            record_id=record_id,
            fetched_at_utc=now_utc(),
            title="USAspending spending_by_award page",
            mime_type="application/json",
            text=resp.text,
            http_status=resp.status_code,
            headers=dict(resp.headers),
            canonical_url=endpoint,
            meta={"request": body},
        )

        more = False
        try:
            data = resp.json()
            results = data.get("results") or []
            more = len(results) > 0
        except Exception:
            more = False

        if more:
            new_cp = Checkpoint(
                connector_name=self.name,
                last_cursor=str(page + 1),
                last_since_utc=checkpoint.last_since_utc or since,
                meta={"window_start": window_start.isoformat(), "window_end": end.isoformat()},
            )
        else:
            new_cp = Checkpoint(
                connector_name=self.name,
                last_cursor="1",
                last_since_utc=end,
                meta={"window_start": window_start.isoformat(), "window_end": end.isoformat()},
            )

        return [rec], new_cp
