from __future__ import annotations

from dataclasses import is_dataclass
from typing import List

from .exceptions import SchemaValidationError
from .models import Event


def validate_event(event: Event) -> None:
    """Validate required fields from Phase 0.

    This is intentionally conservative and avoids inventing new rules.
    """
    if not is_dataclass(event):
        raise SchemaValidationError("Event must be a dataclass instance")

    required_strs: List[str] = [
        "event_id",
        "title",
        "summary",
        "source_name",
        "source_url",
        "source_hash",
        "confidence_rationale",
    ]
    for field in required_strs:
        val = getattr(event, field)
        if not isinstance(val, str) or not val.strip():
            raise SchemaValidationError(f"Missing/empty required string: {field}")

    if not event.entities or not all(isinstance(x, str) and x.strip() for x in event.entities):
        raise SchemaValidationError("entities must be a non-empty list of strings")

    # tickers may be empty (Phase 0 allows), but must be a list
    if event.tickers is None or not isinstance(event.tickers, list):
        raise SchemaValidationError("tickers must be a list (can be empty)")

    if event.theme_tags is None or not isinstance(event.theme_tags, list):
        raise SchemaValidationError("theme_tags must be a list")

    # Score fields are 0-100 ints in Phase 0
    for score_field in [
        "credibility_score",
        "freshness_score",
        "materiality_score",
        "overall_score",
    ]:
        score = getattr(event, score_field)
        if not isinstance(score, int):
            raise SchemaValidationError(f"{score_field} must be int")
        if score < 0 or score > 100:
            raise SchemaValidationError(f"{score_field} out of range 0-100")
