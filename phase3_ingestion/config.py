from __future__ import annotations

import os
from dataclasses import dataclass


def env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v is not None else default


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str = "INFO"

    sec_user_agent: str = "YourApp/0.1 (contact: you@example.com)"

    usaspending_agency_name: str | None = None
    usaspending_agency_tier: str = "toptier"
    usaspending_agency_type: str = "awarding"

    dod_contracts_url: str = "https://www.defense.gov/News/Contracts/"

    senate_disclosure_url: str = "https://www.disclosure.senate.gov/"
    house_ptr_year: int = 2025
    house_ptr_start_id: int = 20025000
    house_ptr_rate_per_sec: float = 0.5

    # Scheduler cadences (minutes)
    sched_sec_minutes: int = 15
    sched_usaspending_minutes: int = 60
    sched_dod_minutes: int = 30
    sched_politicians_minutes: int = 30


def load_settings() -> Settings:
    db = env("DATABASE_URL") or env("POSTGRES_DSN") or ""
    if not db:
        raise RuntimeError("Missing DATABASE_URL (or POSTGRES_DSN).")

    return Settings(
        database_url=db,
        log_level=env("LOG_LEVEL", "INFO") or "INFO",
        sec_user_agent=env("SEC_USER_AGENT", "YourApp/0.1 (contact: you@example.com)") or "YourApp/0.1 (contact: you@example.com)",
        usaspending_agency_name=env("USASPENDING_AGENCY_NAME", None),
        usaspending_agency_tier=env("USASPENDING_AGENCY_TIER", "toptier") or "toptier",
        usaspending_agency_type=env("USASPENDING_AGENCY_TYPE", "awarding") or "awarding",
        dod_contracts_url=env("DOD_CONTRACTS_URL", "https://www.defense.gov/News/Contracts/") or "https://www.defense.gov/News/Contracts/",
        senate_disclosure_url=env("SENATE_DISCLOSURE_URL", "https://www.disclosure.senate.gov/") or "https://www.disclosure.senate.gov/",
        house_ptr_year=int(env("HOUSE_PTR_YEAR", "2025") or "2025"),
        house_ptr_start_id=int(env("HOUSE_PTR_START_ID", "20025000") or "20025000"),
        house_ptr_rate_per_sec=float(env("HOUSE_PTR_RATE_PER_SEC", "0.5") or "0.5"),
        sched_sec_minutes=int(env("SCHED_SEC_MINUTES", "15") or "15"),
        sched_usaspending_minutes=int(env("SCHED_USASPENDING_MINUTES", "60") or "60"),
        sched_dod_minutes=int(env("SCHED_DOD_MINUTES", "30") or "30"),
        sched_politicians_minutes=int(env("SCHED_POLITICIANS_MINUTES", "30") or "30"),
    )
