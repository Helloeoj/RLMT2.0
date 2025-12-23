from __future__ import annotations

from abc import ABC, abstractmethod

from .models import RawRecord, Checkpoint


class Connector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def fetch_batch(self, checkpoint: Checkpoint, limit: int) -> tuple[list[RawRecord], Checkpoint]:
        """Return (records, updated_checkpoint). Must NOT write to the DB."""
        ...
