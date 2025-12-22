from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, List, Dict


class EventType(str, Enum):
    POLITICIAN_DISCLOSURE = "POLITICIAN_DISCLOSURE"
    FED_AWARD = "FED_AWARD"
    GEOPOLITICS_NEWS = "GEOPOLITICS_NEWS"
    ENERGY_RESOURCES = "ENERGY_RESOURCES"
    PREOP_MILESTONE = "PREOP_MILESTONE"
    OTHER_PUBLIC_CATALYST = "OTHER_PUBLIC_CATALYST"


class SourceType(str, Enum):
    GOV = "GOV"
    ISSUER_FILING = "ISSUER_FILING"
    PRESS_RELEASE = "PRESS_RELEASE"
    NEWSWIRE = "NEWSWIRE"
    REPUTABLE_MEDIA = "REPUTABLE_MEDIA"
    OTHER_PUBLIC = "OTHER_PUBLIC"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class PoliticianDisclosureFields:
    reporting_person: Optional[str] = None
    filing_date: Optional[str] = None
    transaction_date_or_range: Optional[str] = None
    transaction_type: Optional[str] = None  # BUY/SELL (Phase 0)
    amount_band: Optional[str] = None
    asset_description: Optional[str] = None


@dataclass
class FederalAwardFields:
    award_id: Optional[str] = None
    contract_number: Optional[str] = None
    agency: Optional[str] = None
    obligated_amount: Optional[str] = None
    ceiling_amount: Optional[str] = None
    contract_type: Optional[str] = None
    period_of_performance: Optional[str] = None
    prime_or_sub: Optional[str] = None


@dataclass
class GeopoliticsFields:
    region_country_tags: Optional[List[str]] = None
    policy_action: Optional[str] = None
    affected_commodities: Optional[List[str]] = None


@dataclass
class PreOpMilestoneFields:
    project_name: Optional[str] = None
    location: Optional[str] = None
    milestone_type: Optional[str] = None
    expected_first_production_date: Optional[str] = None
    capex_funding_details: Optional[str] = None
    offtake_counterparty: Optional[str] = None


@dataclass
class CorroborationFields:
    corroborating_sources: Optional[List[Dict[str, str]]] = None  # [{"name":...,"url":...}]
    contradiction_flags: Optional[List[str]] = None


@dataclass
class NotesFields:
    parsing_notes: Optional[str] = None
    ambiguity_notes: Optional[str] = None


@dataclass
class Event:
    # Required fields (Phase 0)
    event_id: str
    event_type: EventType
    title: str
    summary: str
    event_timestamp_utc: datetime
    discovered_timestamp_utc: datetime
    source_type: SourceType
    source_name: str
    source_url: str
    source_hash: str
    entities: List[str]
    tickers: List[str]
    theme_tags: List[str]
    confidence: Confidence
    confidence_rationale: str
    credibility_score: int
    freshness_score: int
    materiality_score: int
    overall_score: int

    # Optional fields (Phase 0)
    politician_disclosure: Optional[PoliticianDisclosureFields] = None
    federal_award: Optional[FederalAwardFields] = None
    geopolitics: Optional[GeopoliticsFields] = None
    preop_milestone: Optional[PreOpMilestoneFields] = None
    corroboration: Optional[CorroborationFields] = None
    notes: Optional[NotesFields] = None

    def to_dict(self) -> Dict[str, Any]:
        def convert(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.astimezone(timezone.utc).isoformat()
            if isinstance(obj, Enum):
                return obj.value
            if hasattr(obj, "__dataclass_fields__"):
                return {k: convert(v) for k, v in asdict(obj).items() if v is not None}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj

        base = asdict(self)
        # asdict already expands nested dataclasses; we still need to convert enums/datetimes
        return convert(base)


@dataclass
class WatchlistEntry:
    # Phase 0 watchlist requirements
    ticker: str
    company_name: str  # TBD: resolver can populate later; stubs may echo issuer entity
    rank_score: int
    component_scores: Dict[str, int]
    top_events: List[str]  # event_ids
    confidence: Confidence
    confidence_reason: str
    time_horizon: str  # Near-term / Mid-term / Long-term

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d
