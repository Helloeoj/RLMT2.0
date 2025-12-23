# Phase 5 — Ticker Resolution

## 1) Resolver Pipeline (tiered steps)
1. **CIK/Registry Match (Deterministic)**
   - Normalize CIK (10 digits, left-pad) and map directly to `tickers.cik` and/or `entities.external_ids.cik`.
   - If multiple active tickers share the CIK, select primary common stock on primary exchange; flag the rest for review.
2. **Legal/Alias Exact Match**
   - Lowercase/strip punctuation from issuer names and known aliases; exact match against `tickers.symbol_normalized` and `tickers.company_name` as well as `entities.normalized_name/aliases`.
   - Require exchange + security_type compatibility (`COMMON_STOCK` preferred; ignore preferreds/ETFs unless event explicitly targets them).
3. **Fuzzy Name Resolution**
   - Apply trigram/Levenshtein on normalized issuer names vs. `tickers.company_name` and `entities.normalized_name` with minimum similarity 0.85.
   - Boost matches where country/sector lines up with event metadata; demote if exchange or security_type mismatches.
4. **Subsidiary/Parent Linking**
   - Use `entities` relations (parent/subsidiary notes inside `aliases`/`external_ids`) and maintained corporate hierarchy table to map operating subs to listed parents; treat ADR/dual-listed siblings as candidates.
   - Require supporting evidence (shared CIK/ISIN/CUSIP or explicit parent reference in source text).
5. **Manual Review Queue**
   - Any candidate below acceptance threshold or with conflicting results enters review with snapshot of features (match scores, evidence fields, source excerpts).
   - Reviewed outcomes stored as curated aliases or explicit overrides to feed back into Tier 2 for future automation.

## 2) Confidence Rubric (exact thresholds)
- **HIGH (90–100):** Deterministic registry match (CIK/ISIN/CUSIP) OR exact alias/company name + exchange alignment with no conflicts. No contradictory candidates within 10 points.
- **MEDIUM (70–89):** Fuzzy score ≥0.85 with sector/country agreement OR subsidiary→parent linkage with documentary evidence. Nearest alternative ≥10 points lower or disqualified by exchange/security_type rules.
- **LOW (<70):** Ambiguous or weak fuzzy matches (<0.85), conflicting exchanges/security_types, or only indirect textual hints (e.g., location only). Anything without structured identifiers defaults here.
- **Thresholds:**
  - Auto-attach when confidence ≥90.
  - Queue for manual review when 70–89.
  - Suppress (no ticker link) when <70 unless reviewer promotes.

## 3) Data Structures (aliases, mappings, review queue)
- **Alias dictionary:** `{ticker_id, normalized_alias, source, evidence, last_validated_at}` persisted in `entities.aliases` JSONB; curated overrides live in a dedicated `ticker_aliases` table (PK `alias_normalized`, columns: `ticker_id`, `source`, `confidence`, `added_by`, `added_at_utc`).
- **Registry cache:** in-memory map keyed by CIK/ISIN/CUSIP → `ticker_id`, hydrated from `tickers` + authoritative reference files; refreshed daily.
- **Candidate match object (pipeline output):** `{event_id, ticker_id, match_method, match_features, match_confidence, rationale}`; `match_features` includes similarity scores, identifiers hit, exchange/security_type flags, and parent/subsidiary evidence.
- **Review queue item:** `{event_id, candidate_tickers[], best_guess_ticker_id?, evidence_blob, needs_human_decision}` stored in `review_queue` table (`queue_id` PK, `event_id`, `payload_json`, `status`, `created_at_utc`, `reviewed_at_utc`, `reviewer`, `resolution`).

## 4) Storage Model (event_ticker_links fields)
- Persist accepted links in `event_ticker_links` with:
  - `event_id` (UUID FK to `events`)
  - `ticker_id` (BIGINT FK to `tickers`)
  - `link_role` (`PRIMARY` default; allow `SECONDARY`, `INDUSTRY_BASKET`)
  - `map_confidence` (SMALLINT 0–100; use rubric score)
  - `map_method` (TEXT; enum-ish string: `CIK`, `EXACT_ALIAS`, `FUZZY_NAME`, `PARENT_LINKAGE`, `MANUAL_OVERRIDE`)
 - `map_rationale` (TEXT; short evidence summary including identifiers and similarity metrics)
  - `created_at_utc`
- Attach reviewer decisions by storing `map_method = 'MANUAL_OVERRIDE'` and setting `map_confidence` to reviewer-approved score; retain prior auto candidates in `review_queue.payload_json` for audit.

## 5) Guardrails (do-not-trade conditions)
- Do not emit tradable signals or watchlist promotions when:
  - No ticker clears HIGH confidence and review is pending (status `needs_human_decision`).
  - Multiple HIGH candidates exist with <5-point spread (potential ticker collision).
  - Event involves entities without listed equity (only private/agency actors) and no valid industry basket link.
  - Subsidiary/parent mapping lacks supporting identifier evidence (only name similarity) — keep in review.
  - Source credibility or event confidence is LOW; require at least MEDIUM event confidence to attach ticker.

## Appendix: Edge Cases
- **Ticker changes, mergers, and delistings:** Maintain ticker history with effective start/end dates tied to `ticker_id` so historic events resolve to the correct legacy symbol. Surface the active ticker in UI, but keep historical links for backfill and audit.
- **Multiple share classes (e.g., GOOG/GOOGL):** Default to the primary/most liquid class (e.g., voting/non-voting rule) and allow additional `event_ticker_links` with `link_role = 'SECONDARY'` for other active classes. Carry class-level identifiers (CUSIP/ISIN) when available.
- **Instrument restrictions:** Reject ETFs, preferreds, warrants, and structured products unless explicitly supported by the event type; enforce via `security_type` gating at each resolver tier and in guardrails.

## 6) Phase 5 Done Criteria (acceptance tests)
1. Resolver executes tiers in order and surfaces match_method + map_confidence per candidate.
2. Auto-links only occur at ≥90; 70–89 always routed to review; <70 suppressed unless overridden.
3. event_ticker_links rows contain `map_method`, `map_confidence`, and `map_rationale` populated for every attached ticker.
4. Review queue exists with payload showing competing candidates and evidence, and promotes curated aliases back into Tier 2 on approval.
5. Subsidiary/parent rules are documented and block trading when unsupported by identifiers.
6. “Do not trade” guardrails prevent signals when review is pending or ambiguity persists.
