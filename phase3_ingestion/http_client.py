from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

RETRY_STATUS = {408, 429, 500, 502, 503, 504}


@dataclass
class HttpConfig:
    user_agent: str
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    max_retries: int = 6
    backoff_base_sec: float = 2.0
    backoff_max_sec: float = 60.0


class HttpClient:
    def __init__(self, cfg: HttpConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": cfg.user_agent})

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        timeout = kwargs.pop("timeout", (self.cfg.connect_timeout, self.cfg.read_timeout))
        headers = kwargs.pop("headers", {}) or {}

        merged_headers = dict(self.session.headers)
        merged_headers.update(headers)

        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self.session.request(method, url, headers=merged_headers, timeout=timeout, **kwargs)
                if resp.status_code in RETRY_STATUS and attempt <= self.cfg.max_retries:
                    self._sleep(attempt, resp)
                    continue
                return resp
            except requests.RequestException:
                if attempt <= self.cfg.max_retries:
                    self._sleep(attempt, None)
                    continue
                raise

    def _sleep(self, attempt: int, resp: Optional[requests.Response]) -> None:
        base = self.cfg.backoff_base_sec * (2 ** (attempt - 1))
        wait = min(base, self.cfg.backoff_max_sec)

        if resp is not None:
            ra = resp.headers.get("Retry-After")
            if ra:
                try:
                    wait = max(wait, float(ra))
                except Exception:
                    pass

        jitter = random.uniform(0, 0.25 * wait)
        time.sleep(wait + jitter)
