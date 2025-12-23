from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    rate_per_sec: float
    burst: int = 1

    def __post_init__(self) -> None:
        self.capacity = float(self.burst)
        self.tokens = float(self.burst)
        self.last = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> None:
        while True:
            now = time.monotonic()
            elapsed = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_per_sec)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return
            sleep_for = (tokens - self.tokens) / max(self.rate_per_sec, 1e-9)
            time.sleep(min(max(sleep_for, 0.01), 2.0))
