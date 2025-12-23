# Phase 2 — Done Criteria (Acceptance Tests)

These checks define “Phase 2 complete” for **storage design**.

## A) Schema boots cleanly
1) Running `postgres_schema.sql` on a fresh Postgres 16+ database completes with **zero errors**.
2) Extensions referenced by the schema exist and install cleanly:
   - `pgcrypto`
   - `pg_trgm`

## B) Tables exist and constraints enforce integrity
3) The following tables exist with the expected primary keys:
   - `raw_documents`, `events`, `entities`, `tickers`, `event_ticker_links`
   - `features_daily`, `scores_daily`, `signals`
   - FUTURE: `orders`, `fills`, `positions` (present but unused)

4) Foreign keys enforce traceability:
   - `events.raw_document_id → raw_documents.raw_document_id`
   - `tickers.entity_id → entities.entity_id` (nullable allowed)
   - `event_ticker_links.event_id → events.event_id`
   - `event_ticker_links.ticker_id → tickers.ticker_id`

## C) Dedupe anchors work
5) `raw_documents.doc_fingerprint` is **UNIQUE** (duplicate insert fails).
6) `events.event_fingerprint` is **UNIQUE** (duplicate insert fails).

## D) Query performance basics are covered
7) Indexes exist for the “happy path” queries:
   - recent events: `events(event_timestamp_utc)`, `events(discovered_at_utc)`
   - latest signals per ticker: `signals(ticker_id, signal_timestamp_utc)`
   - daily leaderboard: `scores_daily(as_of_date, score_total DESC)`
   - ticker lookup: `tickers(exchange, symbol_normalized)` unique index

## E) End-to-end example runs
8) Running `example_flow.sql` after schema bootstrap inserts:
   - one entity + ticker
   - one raw document + event
   - one event↔ticker link
   - one `scores_daily` row
   - one `signals` row

## F) Migration posture is documented
9) `migration_strategy.md` describes an **additive-first** workflow:
   - add nullable columns
   - backfill
   - then enforce NOT NULL / UNIQUE

## G) (Optional) Phase 5 extension tables are available
10) If you choose to enable Phase 5 flows now, these tables exist:
   - `ticker_aliases`
   - `review_queue`

