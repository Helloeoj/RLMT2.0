# Phase 2 — Database Schema + Data Models (Storage Only)

This package contains a PostgreSQL schema (DDL) that implements the Phase 2 deliverables:
- raw_documents, events, entities, tickers, event_ticker_links, features_daily, scores_daily, signals
- FUTURE: orders, fills, positions (defined but not used)

## Files
- postgres_schema.sql : full DDL (tables, constraints, indexes, extensions)
- example_flow.sql : minimal example inserts showing raw_document -> event -> score -> signal
- dedupe_strategy.md : dedupe keys & fingerprints (how to compute/why)
- migration_strategy.md : how to apply with Alembic (or any migration tool)

## Apply
From psql (recommended for first bootstrap):
```sql
\i postgres_schema.sql
```
Then (optionally):
```sql
\i example_flow.sql
```
