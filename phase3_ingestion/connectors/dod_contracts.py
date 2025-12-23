from __future__ import annotations

from datetime import datetime, timezone
import re

from bs4 import BeautifulSoup
import feedparser

from ..connector_base import Connector
from ..http_client import HttpClient, HttpConfig
from ..models import RawRecord, Checkpoint
from ..utils import now_utc


def _parse_date(text: str) -> datetime | None:
    # Defense.gov commonly uses "Dec. 19, 2025" style dates.
    text = text.strip().replace("Sept.", "Sep.")
    for fmt in ("%b. %d, %Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


class DoDContractsConnector(Connector):
    @property
    def name(self) -> str:
        return "dod_contracts"

    def __init__(self, user_agent: str, contracts_url: str):
        self.client = HttpClient(HttpConfig(user_agent=user_agent))
        self.contracts_url = contracts_url

    def fetch_batch(self, checkpoint: Checkpoint, limit: int) -> tuple[list[RawRecord], Checkpoint]:
        since = checkpoint.last_since_utc
        records: list[RawRecord] = []

        # Fetch landing page and attempt to discover RSS
        resp = self.client.request("GET", self.contracts_url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        rss_url = None
        for link in soup.find_all("link", attrs={"type": "application/rss+xml"}):
            href = link.get("href")
            if href:
                rss_url = href if href.startswith("http") else self.contracts_url.rstrip("/") + "/" + href.lstrip("/")
                break

        items: list[tuple[str, datetime | None]] = []

        if rss_url:
            r = self.client.request("GET", rss_url)
            feed = feedparser.parse(r.text)
            for e in feed.entries or []:
                pub = None
                try:
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc) if getattr(e, "published_parsed", None) else None
                except Exception:
                    pub = None
                link = getattr(e, "link", None)
                if link:
                    items.append((link, pub))
        else:
            # Fallback: parse links on landing page
            for a in soup.select("a"):
                href = a.get("href") or ""
                if "/News/Contracts/" in href and href.count("/") >= 3:
                    link = href if href.startswith("http") else "https://www.defense.gov" + href
                    date_text = a.find_next(string=re.compile(r"\\w+\\.?\\s+\\d{1,2},\\s+\\d{4}"))
                    pub = _parse_date(str(date_text)) if date_text else None
                    items.append((link, pub))

        # Deduplicate and sort
        seen = set()
        deduped: list[tuple[str, datetime | None]] = []
        for link, pub in items:
            if link in seen:
                continue
            seen.add(link)
            deduped.append((link, pub))
        deduped.sort(key=lambda x: x[1] or datetime.min.replace(tzinfo=timezone.utc))

        newest = since
        picked: list[tuple[str, datetime | None]] = []
        for link, pub in deduped:
            if since and pub and pub <= since:
                continue
            picked.append((link, pub))
            if len(picked) >= max(limit, 1):
                break

        # Store landing page (audit)
        records.append(
            RawRecord(
                source_type="dod",
                source_name="defense_contracts_landing",
                url=self.contracts_url,
                record_id=f"landing:{resp.headers.get('Date')}",
                fetched_at_utc=now_utc(),
                title="Defense.gov Contracts landing",
                mime_type="text/html",
                text=html,
                http_status=resp.status_code,
                headers=dict(resp.headers),
                canonical_url=self.contracts_url,
                meta={"kind": "landing", "rss": rss_url},
            )
        )

        for link, pub in picked:
            r2 = self.client.request("GET", link)
            html2 = r2.text
            title = None
            try:
                s2 = BeautifulSoup(html2, "lxml")
                h1 = s2.find("h1")
                if h1:
                    title = h1.get_text(strip=True)
            except Exception:
                title = None

            records.append(
                RawRecord(
                    source_type="dod",
                    source_name="defense_contracts_article",
                    url=link,
                    record_id=link,
                    fetched_at_utc=now_utc(),
                    published_at_utc=pub,
                    title=title,
                    mime_type="text/html",
                    text=html2,
                    http_status=r2.status_code,
                    headers=dict(r2.headers),
                    canonical_url=link,
                    meta={"kind": "article"},
                )
            )

            if pub and (newest is None or pub > newest):
                newest = pub

        new_cp = Checkpoint(
            connector_name=self.name,
            last_cursor=None,
            last_since_utc=newest,
            meta={"rss": rss_url},
        )
        return records, new_cp
