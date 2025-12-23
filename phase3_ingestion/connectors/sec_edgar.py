from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from ..connector_base import Connector
from ..http_client import HttpClient, HttpConfig
from ..models import RawRecord, Checkpoint
from ..utils import now_utc, stable_json_dumps

FORM_TYPES_DEFAULT = ["8-K", "10-Q", "10-K", "S-1"]


class SecEdgarConnector(Connector):
    @property
    def name(self) -> str:
        return "sec_edgar"

    def __init__(self, user_agent: str, forms: list[str] | None = None):
        self.forms = forms or FORM_TYPES_DEFAULT
        self.client = HttpClient(HttpConfig(user_agent=user_agent))

    def _feed_url(self, form: str, count: int) -> str:
        # SEC "current filings" Atom feed
        return (
            "https://www.sec.gov/cgi-bin/browse-edgar"
            f"?action=getcurrent&type={form}&owner=include&count={count}&output=atom"
        )

    def fetch_batch(self, checkpoint: Checkpoint, limit: int) -> tuple[list[RawRecord], Checkpoint]:
        since = checkpoint.last_since_utc
        records: list[RawRecord] = []
        newest: datetime | None = since

        for form in self.forms:
            url = self._feed_url(form=form, count=min(max(limit, 50), 200))
            resp = self.client.request("GET", url)
            text = resp.text

            # Store the feed itself for audit/debug
            records.append(
                RawRecord(
                    source_type="sec",
                    source_name=f"edgar_current_feed_{form}",
                    url=url,
                    record_id=f"feed:{form}:{resp.headers.get('Date')}",
                    fetched_at_utc=now_utc(),
                    title=f"SEC EDGAR current filings feed ({form})",
                    mime_type="application/atom+xml",
                    text=text,
                    http_status=resp.status_code,
                    headers=dict(resp.headers),
                    canonical_url=url,
                    meta={"form": form, "kind": "feed"},
                )
            )

            feed = feedparser.parse(text)
            for e in feed.entries or []:
                updated = None
                try:
                    updated = (
                        datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
                        if getattr(e, "updated_parsed", None)
                        else None
                    )
                except Exception:
                    updated = None

                if since and updated and updated <= since:
                    continue

                entry_id = getattr(e, "id", None) or getattr(e, "link", None)
                link = getattr(e, "link", None) or url
                title = getattr(e, "title", None)

                payload = {
                    "form": form,
                    "id": entry_id,
                    "title": title,
                    "link": link,
                    "updated": updated.isoformat().replace("+00:00", "Z") if updated else None,
                    "summary": getattr(e, "summary", None),
                }

                records.append(
                    RawRecord(
                        source_type="sec",
                        source_name="edgar_current_filing",
                        url=link,
                        record_id=str(entry_id) if entry_id else None,
                        fetched_at_utc=now_utc(),
                        published_at_utc=updated,
                        title=title,
                        mime_type="application/json",
                        text=stable_json_dumps(payload),
                        http_status=resp.status_code,
                        headers=dict(resp.headers),
                        canonical_url=link,
                        meta={"form": form, "kind": "entry"},
                    )
                )

                if updated and (newest is None or updated > newest):
                    newest = updated

        new_cp = Checkpoint(
            connector_name=self.name,
            last_cursor=None,
            last_since_utc=newest or since,
            meta={"forms": self.forms},
        )
        return records, new_cp
