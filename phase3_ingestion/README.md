# Phase 3 — Ingestion Connectors (Raw Fetch → raw_documents)

## Scope
Fetch public data sources and store raw payloads into `raw_documents` with checkpointing + dedupe. No normalization/ticker resolution here.

## Connector Interface
Each connector implements:
- `fetch_batch(cursor, since, limit) -> (records, next_cursor)`

## Sources
Connectors live in `phase3_ingestion/connectors/`:
- SEC (EDGAR)
- USASpending
- DoD contracts
- Politician disclosures

## Storage Contract
- Insert into `raw_documents` (Phase 2 schema).
- Stable `source_id` + dedupe key/checksum so reruns do not duplicate.

## Checkpointing / Retries
- Cursor advances monotonically.
- Retry transient failures; backoff on 429/503; fail fast on other 4xx.

## CLI
Main entry: `phase3_ingestion/ingest.py`
- `--help` should show run/status/validate/schedule style commands.

## Done Criteria
- Each connector fetches successfully.
- Reruns do not duplicate.
- Checkpoints resume after restart.
- One connector failing doesn’t break all runs.
