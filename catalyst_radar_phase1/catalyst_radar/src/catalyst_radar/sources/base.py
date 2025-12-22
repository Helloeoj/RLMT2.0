from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional, Protocol

from catalyst_radar.core.models import SourceType


@dataclass
class RawEvent:
    source_name: str
    source_url: str
    source_type: SourceType
    discovered_timestamp_utc: datetime
    payload: Dict[str, Any]


class SourceAdapter(Protocol):
    name: str

    def fetch(self, *, since_utc: Optional[datetime] = None) -> List[RawEvent]:
        """Return RawEvents discovered since `since_utc` (optional)."""
        ...
