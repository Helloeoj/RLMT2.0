from __future__ import annotations

from dataclasses import dataclass
import os

from catalyst_radar.core.models import Confidence


def _get_env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v is not None else default


def _get_env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _get_env_optional_int(name: str) -> int | None:
    v = os.getenv(name)
    if v is None or not v.strip():
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _get_env_confidence(name: str, default: Confidence) -> Confidence:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().upper()
    try:
        return Confidence(v)
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    # Output + storage
    out_dir: str = _get_env("CATRADAR_OUT_DIR", "./out") or "./out"
    ledger_path: str = _get_env("CATRADAR_LEDGER_PATH", "./out/event_ledger.jsonl") or "./out/event_ledger.jsonl"

    # Logging
    log_level: str = (_get_env("CATRADAR_LOG_LEVEL", "INFO") or "INFO").upper()

    # Safety gates (Phase 0)
    min_confidence: Confidence = _get_env_confidence("CATRADAR_MIN_CONFIDENCE", Confidence.MEDIUM)

    # Phase 0 mentions a credibility threshold but does not specify a default number.
    # If unset, the credibility gate is treated as TBD and not enforced.
    min_credibility: int | None = _get_env_optional_int("CATRADAR_MIN_CREDIBILITY")

    # Staleness windows (examples provided in Phase 0)
    news_stale_days: int = _get_env_int("CATRADAR_NEWS_STALE_DAYS", 30)
    disclosure_stale_days: int = _get_env_int("CATRADAR_DISCLOSURE_STALE_DAYS", 45)

    # Universe gates (Phase 0 defaults) - not used in Phase 1 stubs (no market data yet)
    universe_price_floor: float = float(_get_env("CATRADAR_UNIVERSE_PRICE_FLOOR", "1.0") or "1.0")
    universe_addv_usd_20d_min: float = float(_get_env("CATRADAR_UNIVERSE_ADDV_20D_MIN", "5000000") or "5000000")
    universe_market_cap_min: float = float(_get_env("CATRADAR_UNIVERSE_MARKET_CAP_MIN", "250000000") or "250000000")
