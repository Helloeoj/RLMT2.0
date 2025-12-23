# Phase 2 — Database Schema + Data Models (Storage Only)

**Scope rule:** Storage design only. **No UI, no broker execution, no trading automation.**  
This phase defines the PostgreSQL schema that lets you ingest public documents, normalize them into canonical events, map events to tickers, compute daily features/scores, and persist signals (watchlist / research prompts) with full traceability.

---

## 1) DB Choice + Rationale

**Choice:** **PostgreSQL 16+**

Why Postgres fits Phase 2:
- **Strong relational integrity** (FKs, constraints) for traceability: `raw_documents → events → event_ticker_links → scores/signals`.
- **JSONB** for flexible, source-specific payloads (`headers_json`, `details_json`, `features_json`, `explain_json`) without schema churn.
- **Indexing depth** for time-series style reads (recent events/signals) plus search/fuzzy support later (`pg_trgm`, GIN over JSONB / arrays).
- Easy migration tooling (Alembic/Flyway/Liquibase) and local dev ergonomics.

---

## 2) What this schema stores

### Core ledger (Phase 2)
- **`raw_documents`** — immutable “what we fetched” (URL, headers, bytes/text, hashes, ingest metadata).
- **`events`** — canonical normalized events (type, summary, timestamps, scoring primitives, dedupe fingerprint, suppression/versioning).
- **`entities`** — companies/people/agencies/projects/regions/commodities referenced by events.
- **`tickers`** — tradable instruments (symbol/exchange/type + identifiers like CIK/ISIN/CUSIP).
- **`event_ticker_links`** — resolved mapping from event → ticker with method/confidence + rationale.
- **`features_daily`** — per-ticker daily market/context features (price/volume/volatility + JSON).
- **`scores_daily`** — per-ticker daily model scores and explanations.
- **`signals`** — stored outputs for watchlist/research (NOT broker orders).

### FUTURE tables (defined but not used yet)
- **`orders`, `fills`, `positions`** — placeholders for later phases; safe to ignore in Phase 2.

### Phase 5 additive extensions included here (optional, but ready)
These support the Phase 5 “Ticker Resolution” contract:
- **`ticker_aliases`** — curated alias overrides (manual + learned).
- **`review_queue`** — human review queue for ambiguous event↔ticker resolution.

If you want a **Phase 2-only bootstrap**, you can ignore these two tables; they do not break Phase 2 flows.

---

## 3) Files in this package

- **`postgres_schema.sql`** — full DDL (tables, constraints, indexes, extensions).
- **`example_flow.sql`** — minimal example inserts showing: raw_document → event → score → signal.
- **`dedupe_strategy.md`** — how to compute `doc_fingerprint` and `event_fingerprint`.
- **`migration_strategy.md`** — recommended migration workflow.
- **`done-criteria.md`** — Phase 2 acceptance tests.
- **`migrations/phase5_add_review_queue_and_ticker_aliases.sql`** — additive migration (same tables already present in `postgres_schema.sql` for fresh bootstrap).
- **`behavior-spec.md` + `event-schema.md`** — Phase 0 reference docs included for context (not required to run Phase 2).

---

## 4) Schema overview (tables + key fields)

Below is a *human* overview. For exact types/constraints, see `postgres_schema.sql`.

### `raw_documents`
Purpose: immutable record of each fetched source document.

Key fields:
- `source_type`, `source_name`, `source_url`, `canonical_url`
- `retrieved_at_utc`, `published_at_utc`, `title`
- `raw_content` (bytes) and/or `text_content`
- `content_sha256` (32 bytes)
- `doc_fingerprint` (32 bytes, **UNIQUE**) — dedupe anchor
- `parse_status`, `parse_error`

### `events`
Purpose: canonical, deduped representation of an “event”.

Key fields:
- `event_type`, `title`, `summary`
- `event_timestamp_utc` (when it happened), `discovered_at_utc` (when you saw it)
- `source_type`, `source_name`, `source_url`, `source_hash`
- `confidence`, `credibility_score`, `freshness_score`, `materiality_score`, `overall_score`
- `details_json` (type-specific payload)
- `event_fingerprint` (32 bytes, **UNIQUE**) — event dedupe anchor
- `version`, `supersedes_event_id`, `is_suppressed`

### `entities`
Purpose: normalized names + identifiers for companies/people/agencies/etc.

Key fields:
- `entity_type`, `canonical_name`, `normalized_name` (**UNIQUE per type**)
- `aliases` (JSONB), `external_ids` (JSONB), `country_code`

### `tickers`
Purpose: tradable instruments and identifiers.

Key fields:
- `symbol`, `symbol_normalized`, `exchange` (**UNIQUE exchange+symbol_normalized**)
- `security_type` (default COMMON_STOCK)
- `company_name`, `entity_id` (FK)
- `cik`, `isin`, `cusip` (+ indexes for deterministic matching)
- `sector`, `industry`, `is_active`

### `event_ticker_links`
Purpose: map events to tickers (supports multi-ticker and baskets).

Key fields:
- `(event_id, ticker_id)` composite PK
- `link_role` (PRIMARY/SECONDARY/INDUSTRY_BASKET)
- `map_confidence` (0–100)
- `map_method` (e.g., CIK, EXACT_ALIAS, FUZZY_NAME, MANUAL_OVERRIDE)
- `map_rationale` (short evidence string)

### `features_daily` / `scores_daily` / `signals`
Purpose: persistent daily features, daily scores, and output signals.

Notes:
- Primary keys are composite by `(ticker_id, as_of_date, version)` for daily tables.
- `signals` is append-oriented; optional anti-dup unique index is commented out in DDL.

### Phase 5 extensions (optional)
- `ticker_aliases(alias_normalized PK, ticker_id FK, confidence, evidence_json, …)`
- `review_queue(event_id UNIQUE, payload_json, status, best_guess_ticker_id, …)`

---

## 5) Indexing & Constraints (what matters most)

### Dedupe anchors
- `raw_documents.doc_fingerprint` **UNIQUE**
- `events.event_fingerprint` **UNIQUE**

### Performance indexes (common reads)
- recent documents/events: `retrieved_at_utc`, `published_at_utc`, `event_timestamp_utc`, `discovered_at_utc`
- scoring/signal queries: `scores_daily(as_of_date, score_total DESC)`, `signals(ticker_id, signal_timestamp_utc DESC)`
- JSON/array search: GIN on `events.theme_tags`, `events.details_json`

### Ticker resolution helpers
- `tickers(exchange, symbol_normalized)` unique
- `tickers(cik)`, `tickers(isin)`, `tickers(cusip)` indexed

---

## 6) How to apply (bootstrap)

### Fresh local DB (psql)
```sql
\i postgres_schema.sql
\i example_flow.sql
```

If you are bootstrapping from `postgres_schema.sql`, you **do not need** to run the Phase 5 migration; it is only for upgrading older databases created before the Phase 5 tables were added.

---

## 7) Example data flow (conceptual)

1) **Ingest** public document → write `raw_documents` (dedupe on `doc_fingerprint`).
2) **Parse/Normalize** document → upsert/create canonical `events` (dedupe on `event_fingerprint`).
3) **Resolve** event → ticker(s) → write `event_ticker_links` (with `map_method/confidence/rationale`).
4) **Compute features** daily per ticker → write `features_daily`.
5) **Score** daily per ticker → write `scores_daily`.
6) **Emit signal** (watchlist/research) → write `signals` with `supporting_event_ids` and `score_snapshot`.

For runnable inserts, see `example_flow.sql`.

---

## 8) Practical conventions (recommended)

- Treat `raw_documents` as **append-only** (never overwrite raw bytes; create a new row if you refetch).
- Use `events.version` + `supersedes_event_id` for corrections, rather than editing historical facts in place.
- Keep algorithm iterations out of schema with `model_version` / `feature_set_version` strings.
- Start strict (high confidence gates) and relax later; schema supports both.

---

## 9) Next phases (context only)

- Phase 3: ingestion connectors (fetch + checkpoint + dedupe)
- Phase 4: normalization (canonical event schema enforcement)
- Phase 5: ticker resolution pipeline + human review queue (enabled by optional tables)

