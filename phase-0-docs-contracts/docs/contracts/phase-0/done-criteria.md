# Phase 0 — Done Criteria (Acceptance Tests)

## Acceptance Tests

1) **Universe contract is explicit**
- A reviewer can answer: US-only? OTC? which instruments excluded? minimum liquidity/price/market cap? with no ambiguity.

2) **Catalyst taxonomy is complete for the app themes**
- At least these categories are defined with qualification rules:
  - politician disclosures (public only)
  - military contracts / federal awards
  - wars / geopolitics (news-driven tagging)
  - oil + natural resources operational catalysts
  - pre-operational resource milestones approaching production
- Non-qualifying examples are explicitly listed.

3) **Outputs are well-defined and traceable**
- Ranked watchlist fields are specified (score breakdown, confidence, explanations, supporting events).
- Event ledger is defined as append-only with dedupe/versioning and traceability back to sources.

4) **Safety & compliance rules are unambiguous**
- Public-only constraint is stated.
- Credibility/confidence thresholds exist and govern watchlist promotion.
- “Do nothing” conditions prevent forced recommendations when evidence is weak or absent.

5) **Canonical Event schema is implementation-ready**
- Required vs optional fields are clearly separated.
- Supports multi-ticker events, dedupe, scoring, and source attribution.
- Includes a schema_version.

6) **Phase boundaries are respected**
- No UI requirements, no broker execution, no code, no trading rules beyond descriptive ranking inputs.
