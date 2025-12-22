from __future__ import annotations

from dataclasses import replace

from ..core.models import Event


def apply_placeholder_scores(event: Event) -> Event:
    """Phase 1 placeholder.

    Phase 0 defines required score fields but does not define numeric formulas/weights.
    Therefore, Phase 1 keeps scores as-is if provided by fixtures; otherwise they remain 0.
    """
    # Keep as-is; caller already defaulted to 0.
    return replace(event)
