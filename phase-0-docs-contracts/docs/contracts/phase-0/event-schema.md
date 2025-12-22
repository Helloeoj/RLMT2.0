# Phase 0 — Canonical Event Schema

schema_name: CanonicalEvent  
schema_version: 0.1

This schema defines the canonical normalized representation of an external “Event” used by the catalyst radar logic.

---

## Required fields
- **event_id**: Stable unique identifier across dedupe/versioning
- **event_type**: Enum  
  - {POLITICIAN_DISCLOSURE, FED_AWARD, GEOPOLITICS_NEWS, ENERGY_RESOURCES, PREOP_MILESTONE, OTHER_PUBLIC_CATALYST}
- **title**: Human-readable headline
- **summary**: 1–3 sentence factual summary
- **event_timestamp_utc**: When the underlying event occurred (best-known time)
- **discovered_timestamp_utc**: When the system first detected it
- **source_type**: Enum  
  - {GOV, ISSUER_FILING, PRESS_RELEASE, NEWSWIRE, REPUTABLE_MEDIA, OTHER_PUBLIC}
- **source_name**: Publisher/agency/site name
- **source_url**: Canonical public URL
- **source_fingerprint**: Hash/fingerprint for deduplication
- **entities**: List of involved entities (issuer, agency, person, project); must minimally include issuer name
- **tickers**: List of mapped tickers  
  - May be empty (if unmapped); if empty, cannot drive watchlist promotion
- **theme_tags**: Set of tags, e.g.  
  - {DEFENSE, OIL_GAS, MINING, CRITICAL_MINERALS, SANCTIONS, SHIPPING, LNG, ...}
- **confidence**: Enum {LOW, MEDIUM, HIGH} + short rationale
- **credibility_score**: 0–100 (source strength + corroboration)
- **freshness_score**: 0–100 (staleness-based)
- **materiality_score**: 0–100 (magnitude relative to issuer/sector)
- **overall_score**: 0–100 (weighted rollup used for ranking)

---

## Optional fields (type-specific)
### politician_disclosure (optional block)
- reporting_person: name/role
- filing_date: date
- transaction_date_or_range: date or window
- transaction_type: {BUY, SELL}
- amount_band: as disclosed
- asset_description: as disclosed

### federal_award (optional block)
- award_id / contract_number: identifier(s)
- agency: awarding agency
- obligated_amount: numeric (if stated)
- ceiling_amount: numeric (if stated)
- contract_type: IDIQ/mod/task order/etc.
- period_of_performance: start/end if known
- prime_or_sub: if known

### geopolitics (optional block)
- region_tags: countries/regions
- policy_action: sanction/export control/etc.
- affected_commodities: oil/LNG/uranium/copper/etc.

### resources_or_preop (optional block)
- project_name
- project_location
- milestone_type: permit/FID/financing/EPC/commissioning/first production/etc.
- expected_first_production_date: if public
- funding_details_public: if public
- offtake_counterparty_public: if public

### corroboration (optional block)
- corroborating_sources[]: list of sources/URLs
- contradiction_flags: markers for unresolved conflicts

### notes (optional block)
- ambiguity_notes: unresolved mapping/details
- parsing_notes: internal trace
