from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class RawRecord:
    source_type: str
    source_name: str
    url: str
    record_id: str | None
    fetched_at_utc: datetime
    published_at_utc: datetime | None = None
    title: str | None = None
    mime_type: str | None = None
    raw_bytes: bytes | None = None
    text: str | None = None
    http_status: int | None = None
    headers: Dict[str, Any] | None = None
    canonical_url: str | None = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    connector_name: str
    last_cursor: str | None = None
    last_since_utc: datetime | None = None
    etag: str | None = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunStats:
    fetched: int = 0
    stored: int = 0
    deduped: int = 0
    errors: int = 0
