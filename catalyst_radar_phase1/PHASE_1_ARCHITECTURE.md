# Phase 1 — Repo Structure + Architecture Skeleton (No UI)

## Architecture Overview
Phase 1 proves packaging + a minimal runnable CLI/pipeline skeleton. No UI, no scoring, no broker execution.

## Folder Tree (Phase 1 relevant)
- `catalyst_radar_phase1/`
  - `catalyst_radar/`
    - `README.md` (quickstart)
    - `src/catalyst_radar/` (package root, CLI + stubs)

## Module Responsibilities
- CLI entrypoint: run a minimal pipeline (“hello”) to validate structure.
- Stubs/interfaces shaped for later phases (ingestion → normalization → resolution).

## Core Interfaces (shape)
- Connector: `fetch_batch(cursor, since, limit) -> (records, next_cursor)`
- Normalizer: `normalize(raw_document) -> event | quarantine`
- Resolver: `resolve(entity/event) -> ticker_matches[]`

## Config & Logging Plan
- Env-based config for dev.
- Structured logs w/ identifiers where possible.
- Non-zero exit codes on failure.

## Done Criteria
- Repo runs Phase 1 hello pipeline per README.
- Clean imports, repeatable execution, clear errors.
