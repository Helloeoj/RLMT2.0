from __future__ import annotations

from .config import Settings
from .connectors.sec_edgar import SecEdgarConnector
from .connectors.usaspending import UsaSpendingAwardsConnector
from .connectors.dod_contracts import DoDContractsConnector
from .connectors.politician_disclosures import PoliticianDisclosuresConnector


def build_connectors(settings: Settings):
    ua = settings.sec_user_agent
    return {
        "sec_edgar": SecEdgarConnector(user_agent=ua),
        "usaspending_awards": UsaSpendingAwardsConnector(
            user_agent=ua,
            agency_name=settings.usaspending_agency_name,
            agency_tier=settings.usaspending_agency_tier,
            agency_type=settings.usaspending_agency_type,
        ),
        "dod_contracts": DoDContractsConnector(user_agent=ua, contracts_url=settings.dod_contracts_url),
        "politician_disclosures": PoliticianDisclosuresConnector(
            user_agent=ua,
            senate_url=settings.senate_disclosure_url,
            house_year=settings.house_ptr_year,
            house_start_id=settings.house_ptr_start_id,
            house_rate_per_sec=settings.house_ptr_rate_per_sec,
        ),
    }
