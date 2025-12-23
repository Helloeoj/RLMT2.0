# Phase 4 — Normalization

## 1) Final Canonical Event Schema

| Field | Type | Required? | Notes |
| --- | --- | --- | --- |
| `event_id` | string | Required | System-generated UUID (surrogate key; Phase 2 uses `gen_random_uuid()`); not the dedupe anchor. |
| `event_type` | enum | Required | {`POLITICIAN_DISCLOSURE`, `FED_AWARD`, `GEOPOLITICS_NEWS`, `ENERGY_RESOURCES`, `PREOP_MILESTONE`, `OTHER_PUBLIC_CATALYST`} (matches Phase 0 contract). |
| `title` | string | Required | Human-readable headline. |
| `summary` | string | Required | 1–3 sentence factual summary. |
| `event_timestamp_utc` | datetime | Required | Best-known occurrence time (filing date, award date, announcement date). |
| `discovered_at_utc` | datetime | Required | First time the system saw the record (Phase 2 column name). |
| `source_type` | enum | Required | {`GOV`, `ISSUER_FILING`, `PRESS_RELEASE`, `NEWSWIRE`, `REPUTABLE_MEDIA`, `OTHER_PUBLIC`} |
| `source_name` | string | Required | Publisher/agency/site name. |
| `source_url` | string | Required | Canonical public URL. |
| `source_hash` | bytes | Required | SHA-256 hash of normalized source payload for deduping (Phase 2 column name). |
| `event_fingerprint` | bytes | Required | SHA-256 hash that represents the durable event identity (Phase 2 idempotency anchor for dedupe/idempotency). |
| `entities` | object[] | Required | Each: `{name, entity_type (PERSON/COMPANY/AGENCY/PROJECT), role}`; stored in `details_json.entities` until an `event_entity_links` table exists. |
| `tickers` | string[] | Required (can be empty) | Canonical view of linked tickers; persisted via `event_ticker_links` rows (primary/secondary/etc.). Empty list allowed; empty cannot drive watchlist promotion. |
| `theme_tags` | string[] | Required (can be empty) | Domain tags (e.g., DEFENSE, OIL_GAS, SANCTIONS). |
| `confidence` | enum+string | Required | Enum {LOW, MEDIUM, HIGH} + rationale text. |
| `credibility_score` | integer | Required | 0–100. Source quality + corroboration (Phase 2 NOT NULL; placeholder policy allowed). |
| `freshness_score` | integer | Required | 0–100. Recency-based (Phase 2 NOT NULL; placeholder policy allowed). |
| `materiality_score` | integer | Required | 0–100. Magnitude relative to issuer/sector (Phase 2 NOT NULL; placeholder policy allowed). |
| `overall_score` | integer | Required | 0–100. Weighted rollup of above (Phase 2 NOT NULL; placeholder policy allowed). |
| `corroborating_sources` | object[] | Optional | `{url, source_name, confidence}` when multiple confirmations exist. |
| `contradiction_flags` | string[] | Optional | Reasons for conflicting details. |
| `notes` | object | Optional | `{ambiguity, parsing, ...}` freeform; store full object in `details_json.notes`. Map `notes.ambiguity` (string) into `ambiguity_notes` for a short operator-facing summary. |
| `attachments` | object[] | Optional | `{type, url, description}` for PDFs/images. |

### Type-specific blocks
- **SEC filings (stored under `OTHER_PUBLIC_CATALYST` unless/until a schema_version bump adds `SEC_FILING`)**: `{filing_form, filer_name, cik, accession_number, filing_date, period_end_date, reported_items[], shares_or_amount, transaction_type (BUY/SELL/OTHER), relationship_to_issuer}`; keep these fields in `details_json` and optionally add `theme_tags` including `SEC_FILING` for filtering.
- **FED_AWARD**: `{award_id, contract_number, agency, subagency, obligated_amount, ceiling_amount, contract_type, period_of_performance {start, end}, prime_or_sub, funding_agency, recipient, place_of_performance}`
- **POLITICIAN_DISCLOSURE**: `{reporting_person, office, filing_date, transaction_date_or_range, transaction_type (BUY/SELL), amount_band, asset_description, issuer_cik_or_ticker, spouse_or_dependents_involved}`
- **GEOPOLITICS_NEWS / ENERGY_RESOURCES / PREOP_MILESTONE / OTHER_PUBLIC_CATALYST**: `{region_tags[], policy_action, affected_commodities[], project_name, project_location, milestone_type, expected_first_production_date, funding_details_public, offtake_counterparty_public}` (only populate relevant fields).

## 2) Source → Event Mapping Tables

### SEC filings → `OTHER_PUBLIC_CATALYST` (Phase 0-aligned; tag `details_json.filing_form`)
| Source Field | Canonical Field |
| --- | --- |
| Form type (e.g., 4, 8-K) | `filing_form` + `event_type=OTHER_PUBLIC_CATALYST` (schema_version 0.1); **optional**: if schema_version bumps to 0.2, map to `event_type=SEC_FILING`. |
| Filer name | `filer_name`, `entities[]` (entity_type=COMPANY) |
| CIK | `cik`, `source_hash` seed |
| Accession number | `accession_number`, `source_hash` seed |
| Filing date | `filing_date`, `event_timestamp_utc` |
| Period end date | `period_end_date` |
| Reported items/transactions | `reported_items[]`, `transaction_type`, `shares_or_amount` |
| Issuer + insider roles | `entities[]` (role=REPORTING_OWNER/ISSUER), `relationship_to_issuer` |
| SEC URL | `source_url`, `attachments` |
| Ingestion timestamp | `discovered_at_utc` |

### USASpending → `FED_AWARD`
| Source Field | Canonical Field |
| --- | --- |
| `generated_unique_award_id` / `piid` | `award_id` / `contract_number` |
| `awarding_agency` / `awarding_sub_agency` | `agency` / `subagency` |
| `funding_agency` | `funding_agency` |
| `recipient` (legal entity) | `recipient`, `entities[]` (COMPANY) |
| `place_of_performance` | `place_of_performance` |
| `obligation` / `base_and_all_options_value` | `obligated_amount` / `ceiling_amount` |
| `type_of_contract_pricing` | `contract_type` |
| `period_of_performance_start` / `_end` | `period_of_performance.start/end`, `event_timestamp_utc` (start) |
| Record publish date | `discovered_at_utc` |
| Record URL/API self link | `source_url`, `source_hash`, `event_fingerprint` seed |

### Defense announcements/press releases → `FED_AWARD`
| Source Field | Canonical Field |
| --- | --- |
| Announcement headline | `title`, `summary` seed |
| Awarding organization | `agency` / `source_name` |
| Contract number/award id (if stated) | `contract_number` / `award_id` |
| Dollar values | `obligated_amount` / `ceiling_amount` |
| Period of performance | `period_of_performance.start/end` |
| Award date | `event_timestamp_utc` |
| Award recipients | `recipient`, `entities[]` (COMPANY) |
| Location/contract scope | `place_of_performance`, `theme_tags` (DEFENSE) |
| Published URL | `source_url`, `source_hash`, `event_fingerprint` seed, `attachments` |
| Detected time | `discovered_at_utc` |

### Politician disclosures → `POLITICIAN_DISCLOSURE`
| Source Field | Canonical Field |
| --- | --- |
| Reporting person / office | `reporting_person`, `office`, `entities[]` (PERSON) |
| Filing date | `filing_date`, `event_timestamp_utc` |
| Transaction date/range | `transaction_date_or_range` |
| Transaction type | `transaction_type` |
| Amount band | `amount_band` |
| Asset description | `asset_description`, `entities[]` (COMPANY/ASSET), `tickers` mapping |
| Spouse/dependent indicator | `spouse_or_dependents_involved` |
| Disclosure URL | `source_url`, `source_hash`, `event_fingerprint` seed |
| Ingestion time | `discovered_at_utc` |

## 3) Validation Rules
- Canonical fields marked Required must be non-null after normalization; empty list acceptable only for `tickers` and `theme_tags`.
- `event_type` must align with mapping rules and allowed enums (Phase 0 enum); if schema_version 0.2 adds `SEC_FILING`, validation must accept it.
- `event_timestamp_utc` must be a valid datetime (no future dates >24h from `discovered_at_utc`).
- `source_url` must be HTTPS and parseable; `source_hash` and `event_fingerprint` must exist and be deterministic per source payload/event identity.
- `entities` must include at least one issuer/agency/company/person relevant to the event and capture roles; stored inside `details_json.entities` until an `event_entity_links` table is available.
- Monetary fields (`obligated_amount`, `ceiling_amount`, `shares_or_amount`) must normalize to numeric with currency context (USD default) or be null.
- Scores (`credibility_score`, `freshness_score`, `materiality_score`, `overall_score`) must be integers 0–100; `confidence` rationale text must be present. Because the database columns are NOT NULL, apply a deterministic placeholder policy when true scoring is unavailable (e.g., `credibility_score=60`, `freshness_score` based on recency bucket, `materiality_score=50`, `overall_score=ceil(0.4*credibility + 0.3*freshness + 0.3*materiality)`).
- Type-specific required pairs:
  - SEC filings: `filing_form`, `filer_name`, `accession_number`, `filing_date` present.
  - `FED_AWARD`: `award_id` or `contract_number`, plus `agency` and `recipient`.
  - `POLITICIAN_DISCLOSURE`: `reporting_person`, `transaction_type`, `amount_band`, `asset_description`, `transaction_date_or_range`.

## 4) Quarantine/Reject Rules
- Reject if `event_type` not recognized or mapping fails to determine target type (use Phase 0 enum unless schema_version bump allows `SEC_FILING`).
- Quarantine if required fields are missing post-normalization but recoverable via enrichment (e.g., missing `tickers`, partial entity roles, absent `period_of_performance.end`).
- Reject if `source_url` fails HTTPS validation or obvious non-public link.
- Reject duplicates when `event_fingerprint` matches an existing canonical event and no new material data is present; use `source_hash` to catch exact-payload repeats. If the new record is materially different, create a new version and set `supersedes_event_id`.
- Quarantine if `event_timestamp_utc` is >24h in future or >10 years in past without corroboration.
- Quarantine if numeric fields contain non-parseable text after standard cleaners.
- Flag for review if `confidence=LOW` with `credibility_score <40`.

## 5) Phase 4 Done Criteria (acceptance tests)
- Canonical schema implemented in code with validation enforcing Required fields, score ranges, and Phase 0 enum alignment (or schema_version 0.2 additions documented).
- Normalization mappers exist for each source (SEC, USASpending, Defense PRs, politician disclosures) producing the canonical types above and populating `details_json` for entities and type-specific payloads.
- Unit tests cover happy-path and failure-path for each source mapper and validation rules, including placeholder scoring policy and dedupe via `source_hash`/`event_fingerprint`.
- Quarantine/reject paths log reasons and expose counts in ingestion metrics.
- End-to-end run converts sample raw records for each source into canonical events with zero validation errors and correct event types mapped to Phase 0 enum.
