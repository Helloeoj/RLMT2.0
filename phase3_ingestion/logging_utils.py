from __future__ import annotations

import json
import logging
from typing import Any


def get_logger(name: str = "phase3_ingestion") -> logging.Logger:
    return logging.getLogger(name)


def log_json(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, default=str, ensure_ascii=False))
