# Phase 0 — Logic Contract (No UI / No Code / No Broker)

This folder contains the Phase 0 contract/spec for the private “AI catalyst radar + auto-trader” system.

## Scope (Phase 0)
- Public data only
- Logic + schemas + output contracts
- No UI
- No broker execution
- No trading strategy / signals beyond descriptive ranking inputs

## Artifacts
- `behavior-spec.md` — behavior contract (universe, catalysts, outputs, safety & compliance)
- `event-schema.md` — canonical Event schema (required/optional fields)
- `done-criteria.md` — Phase 0 acceptance tests

## Versioning
- The Event schema is versioned via `schema_version` in `event-schema.md`.
- Breaking changes MUST bump `schema_version` and update `done-criteria.md`.
