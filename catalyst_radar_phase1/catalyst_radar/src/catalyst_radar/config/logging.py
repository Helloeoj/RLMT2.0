from __future__ import annotations

import logging
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """Basic console logging. Phase 1: human-readable."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)sZ | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_logger(name: str, *, level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level.upper(), logger.level))
    return logger
