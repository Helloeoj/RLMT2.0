from __future__ import annotations

from typing import Iterable, Optional, Protocol

from catalyst_radar.core.models import Event


class EventStore(Protocol):
    def append(self, event: Event) -> None: ...

    def get(self, event_id: str) -> Optional[Event]: ...

    def iter_all(self) -> Iterable[Event]: ...
