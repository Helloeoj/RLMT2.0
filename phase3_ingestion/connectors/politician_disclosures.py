from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..connector_base import Connector
from ..http_client import HttpClient, HttpConfig
from ..models import RawRecord, Checkpoint
from ..rate_limit import TokenBucket
from ..utils import now_utc


class PoliticianDisclosuresConnector(Connector):
    @property
    def name(self) -> str:
        return "politician_disclosures"

    def __init__(self, user_agent: str, senate_url: str, house_year: int, house_start_id: int, house_rate_per_sec: float):
        self.client = HttpClient(HttpConfig(user_agent=user_agent))
        self.senate_url = senate_url
        self.house_year = house_year
        self.house_start_id = house_start_id
        self.house_bucket = TokenBucket(rate_per_sec=max(house_rate_per_sec, 0.05), burst=1)

    def _discover_senate_download(self) -> str | None:
        # Discover a download link (zip/xml) on the Senate disclosure homepage.
        resp = self.client.request("GET", self.senate_url)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            text = (a.get_text(" ", strip=True) or "").lower()
            if "download" in text and (href.endswith(".zip") or href.endswith(".xml") or "download" in href.lower()):
                if href.startswith("http"):
                    return href
                return self.senate_url.rstrip("/") + "/" + href.lstrip("/")
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            if href.endswith(".zip"):
                return href if href.startswith("http") else self.senate_url.rstrip("/") + "/" + href.lstrip("/")
        return None

    def _house_ptr_url(self, filing_id: int) -> str:
        return f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{self.house_year}/{filing_id}.pdf"

    def fetch_batch(self, checkpoint: Checkpoint, limit: int) -> tuple[list[RawRecord], Checkpoint]:
        records: list[RawRecord] = []

        # --- Senate bulk download (stores file as-is) ---
        download_url = self._discover_senate_download()
        if download_url:
            r = self.client.request("GET", download_url)
            records.append(
                RawRecord(
                    source_type="congress",
                    source_name="senate_disclosure_db",
                    url=download_url,
                    record_id=download_url,
                    fetched_at_utc=now_utc(),
                    title="Senate disclosure database download",
                    mime_type=r.headers.get("Content-Type") or "application/octet-stream",
                    raw_bytes=r.content,
                    http_status=r.status_code,
                    headers=dict(r.headers),
                    canonical_url=download_url,
                    meta={"kind": "bulk_db"},
                )
            )

        # --- House PTR PDFs (ID scan, checkpointed) ---
        cursor = int(checkpoint.meta.get("house_last_checked_id") or checkpoint.last_cursor or str(self.house_start_id))
        last_checked = cursor

        max_checks = max(limit, 1)
        for i in range(max_checks):
            filing_id = cursor + 1 + i
            last_checked = filing_id
            url = self._house_ptr_url(filing_id)

            self.house_bucket.acquire(1.0)

            head = self.client.request("HEAD", url)
            if head.status_code != 200:
                continue

            getr = self.client.request("GET", url)
            if getr.status_code != 200:
                continue

            records.append(
                RawRecord(
                    source_type="congress",
                    source_name="house_ptr_pdf",
                    url=url,
                    record_id=str(filing_id),
                    fetched_at_utc=now_utc(),
                    title=f"House PTR {self.house_year} #{filing_id}",
                    mime_type="application/pdf",
                    raw_bytes=getr.content,
                    http_status=getr.status_code,
                    headers=dict(getr.headers),
                    canonical_url=url,
                    meta={"kind": "ptr_pdf", "year": self.house_year, "filing_id": filing_id},
                )
            )

        new_cp = Checkpoint(
            connector_name=self.name,
            last_cursor=str(last_checked),
            last_since_utc=checkpoint.last_since_utc,
            meta={
                **(checkpoint.meta or {}),
                "house_year": self.house_year,
                "house_last_checked_id": last_checked,
                "senate_download_url": download_url,
                "house_rate_per_sec": self.house_bucket.rate_per_sec,
            },
        )
        return records, new_cp
