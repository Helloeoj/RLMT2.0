# Phase 0 — Behavior Spec (Logic Contract)

**PHASE:** 0 — Behavior Spec (Logic Contract)  
**SCOPE RULE:** No code. No UI. No broker execution. Public data only.  
**APP THEMES:** Politician disclosures (public only) • Military contracts/federal awards • Wars/geopolitics (news-driven tagging) • Oil + natural resources • Pre-operational resources approaching production

---

## 1) Assumptions
- The system uses **publicly available data only** (government sites, issuer filings, reputable media/newswire, official press releases). No paid/inside sources; no MNPI.
- Phase 0 defines **logic + schemas + output contracts only**. **No code, no UI, no brokerage integration, no order logic**.
- “Auto-trader” is a later phase; Phase 0 outputs are designed to support future signal generation while remaining **descriptive/observational** now.
- Default configuration is optimized for **lower manipulation risk** and **sane tradability**; all thresholds are configurable later.

---

## 2) Stock Universe Rules
### Universe scope
- **Primary universe (default):** US-listed common equities on **NYSE / NASDAQ / NYSE American**.
- **ADRs (optional):** Allowed only if listed on the above venues and pass liquidity + data-quality gates.
- **OTC policy (default):** **OTC disabled**.
  - **If enabled later:** allow **OTCQX/OTCQB only** (no Pink/Gray), and require stricter liquidity/risk gating.

### Instrument types (default)
- **Include:** Common shares.
- **Exclude (default):** ETFs/ETNs, leveraged/inverse products, preferreds, rights/warrants, SPAC rights/units, closed-end funds, tokens/crypto instruments.

### Tradability gates (hard filters; configurable defaults)
- **Price floor:** last close **≥ $1.00**
- **Liquidity:** 20-trading-day **Avg Daily Dollar Volume (ADDV) ≥ $5M**
- **Market cap:** **≥ $250M**
- **Trading status:** Exclude halted/suspended until normal trading resumes.

### Data quality gates (hard filters)
- Must have reliable mapping from company → ticker (no ambiguous tickers).
- Must have at least one primary identifier when possible (e.g., **CIK** for US issuers; otherwise FIGI/LEI/etc. if available).

### Theme overlays (soft scoring; not exclusions)
- Tag and score higher relevance for:
  - Defense/aerospace, cybersecurity, energy (oil & gas), mining/metals, critical minerals, logistics, satellite/ISR, key industrials.
- “Pre-operational resources” are **not excluded** by default, but must still pass risk gates unless OTC mode is explicitly enabled later.

---

## 3) Catalyst/Event Types (what qualifies)
An “Event” is valid if it is **public**, **time-stamped**, **source-attributable**, and **ticker-mappable**, and represents **new, material, time-bounded information** that plausibly changes future cashflows, risk, or attention.

### A) Politician Disclosures (public only)
**Qualifying:**
- New trade disclosure filings indicating **buy/sell** of an identifiable security or issuer exposure.
- Must include at least: reporting person, transaction type, transaction date (or window), filing date, and asset identity (or resolvable identity).

**Scoring emphasis:**
- **Freshness** (staleness penalty if filing long after trade)
- **Repeat activity** (same politician / related network)
- **Cluster behavior** (multiple related disclosures)
- **Theme alignment** (defense, energy, critical minerals)

### B) Military Contracts / Federal Awards
**Qualifying:**
- Confirmed awards/modifications/IDIQ task orders with identifiable award IDs and amounts (or bounded amounts like ceiling/obligated).

**Scoring emphasis:**
- **Contract size vs issuer revenue/market cap**
- **Ceiling vs obligated amount** (distinguish)
- **Duration** and option years (if known)
- **Prime vs sub** (prime weighted higher)
- **Agency / mission relevance** (DoD, DHS, etc.)

### C) Wars / Geopolitics (news-driven tagging)
**Qualifying:**
- Public news that changes operating environment or demand, such as:
  - sanctions/export controls, conflict escalation/de-escalation, shipping-lane disruptions, OPEC policy shifts, strategic reserve actions, nationalization/resource policy changes.
- Must be sourced from reputable outlets or official statements.

**Scoring emphasis:**
- **Direct linkage** to impacted tickers/industries
- **Severity + credibility** (official confirmations weighted higher)
- **Persistence** (policy change > one-off headline)

### D) Oil + Natural Resources (operational catalysts)
**Qualifying:**
- Reserve/resource updates, major permits, drilling results, production guidance changes, pipeline/LNG milestones, offtake agreements, major capex/funding, M&A, asset sales.

**Scoring emphasis:**
- **Timeline clarity** (dates and milestones)
- **Funding certainty** (financing closed > rumored)
- **Regulatory status** (permit granted > filed)
- **Operational inflection** (first production, ramp, expansion)

### E) Pre-operational resource companies approaching production
**Qualifying:**
- Definitive steps that reduce “time-to-cashflow,” such as:
  - final permits, FID, EPC signed, project finance closed,
  - offtake/streaming agreements, commissioning milestones,
  - construction progress updates, first pour/first oil announced,
  - feasibility study updates that materially shift NPV/IRR/capex timeline (public, explicit).

**Scoring emphasis:**
- **De-risking level** (permit+funding+EPC+commissioning strongest)
- **Milestone proximity** (expected first production window)
- **Counterparty quality** (credible offtakers/financiers)
- **Dilution/financing risk** (only if public and explicit)

### Non-qualifying (filtered out)
- Pure opinions/price targets, vague rumors, “unnamed sources” without corroboration, social-media hype, recycled press releases without new facts.
- General macro news with no defensible mapping to tickers or industries.

---

## 4) Outputs
### Primary artifact: Ranked Watchlist (refreshable)
Each entry includes:
- Ticker + company name
- **Rank score** (0–100) and **component scores**:
  - Freshness, Materiality, Theme Fit, Source Credibility, De-risking
- Top **supporting Events** (with short explanations)
- **Confidence level** (Low/Med/High) + rationale
- **Time horizon tag**: Near-term (days–weeks), Mid-term (weeks–months), Long-term (months+)

### Secondary artifact: Event Ledger (append-only log)
- Every ingested Event stored as canonical schema, with deduplication and versioning.
- Full traceability: “why is this ticker here?”

### Future-facing hooks (no signals yet)
- Output fields support later:
  - signal generation (entry/exit candidates),
  - backtesting labels,
  - alerting thresholds,
  - position-sizing inputs.
- Phase 0 remains **descriptive** (no buy/sell commands).

---

## 5) Safety & Compliance Rules
### Public-data-only rule
- Only ingest and reason over data that is publicly accessible.
- No MNPI, private leaks, paid insider feeds, or instructions to front-run individuals.

### Source credibility & confidence thresholds
- Each Event receives a **Source Credibility score** and **Confidence** label.
- If credibility is below threshold OR ticker mapping is uncertain:
  - Event may be logged, but **cannot promote** a ticker to the watchlist.
- Watchlist requires minimum confidence (default: **MEDIUM+**; configurable later).

### “Do nothing” conditions
- No qualifying Events above threshold → output:
  - “No actionable catalysts detected” and a neutral digest.
- Conflicting reports unresolved → down-rank and flag **CONFLICT**.
- Event staleness beyond window (configurable defaults):
  - news: >30 days strongly penalized/excluded
  - disclosures: >45 days strongly penalized/excluded
- Suspected manipulation pattern (ultra-low liquidity, hype-only sources, disallowed OTC tiers) → exclude and flag.

### Risk controls (logic-level)
- Default excludes OTC and penny stocks to reduce pump risk.
- Every watchlist inclusion must cite at least one Event with source + timestamp (traceability requirement).
- Outputs are informational rankings; no guaranteed outcomes.
