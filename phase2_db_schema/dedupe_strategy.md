# Dedupe Strategy (Phase 2)

Phase 2 stores **raw documents** and **canonical events** in a way that supports:
- deterministic dedupe (hard uniqueness)
- auditability (you can always explain *why* two items were merged or kept separate)
- future backfills (re-ingesting historic ranges without creating duplicates)

---

## 1) Raw document dedupe (`raw_documents`)

### Inputs
- `source_type` + `source_name` (where it came from)
- `source_url` (as fetched)
- `canonical_url` (normalized)
- `published_at_utc` (if known)
- document content bytes/text

### Required stored hashes
- `content_sha256` (**32 bytes**)  
  SHA-256 of **raw bytes** (`raw_content`) *or* normalized text (`text_content`).  
  Pick **one convention** and never mix, or your dedupe will drift.

- `doc_fingerprint` (**32 bytes**, UNIQUE)  
  Recommended identity string (UTF‑8):
  ```
  source_type | source_name | canonical_url | published_bucket | content_sha256_hex
  ```
  Then SHA-256 of that string.

### Recommended canonicalization rules
- Normalize scheme/host casing
- Strip tracking params: `utm_*`, `fbclid`, `gclid`, etc.
- Normalize trailing slashes
- Prefer stable URL forms if the source is known to generate multiple aliases

### Published time bucketing
If a source’s timestamps are noisy, bucket to reduce “same doc, different timestamp” duplicates:
- stable sources: full timestamp
- noisy sources: date bucket `YYYY-MM-DD`

---

## 2) Event dedupe (`events`)

**Goal:** one row per underlying real-world event, even if it appears in multiple sources.

### Required stored hash
- `event_fingerprint` (**32 bytes**, UNIQUE)

### Recommended identity string
```
event_type | primary_identifier | event_timestamp_bucket | key_fields
```
Then SHA-256.

### Primary identifiers by event type (examples)
- **FED_AWARD:** `award_id` / `contract_number` (best); else composite: agency + vendor + amount + PoP dates
- **POLITICIAN_DISCLOSURE:** person + tx_date + asset/ticker + tx_type + amount_band
- **GEOPOLITICS_NEWS:** action + region + effective_date (+ official vs media)
- **PREOP_MILESTONE:** project + milestone_type + announced_date

### Timestamp bucketing
Use buckets to avoid false splits due to small timestamp discrepancies:
- common default: **1-hour bucket**
- very noisy sources: **date bucket**

---

## 3) Ticker link “dedupe” (`event_ticker_links`)

`event_ticker_links` uses a composite primary key:
- `(event_id, ticker_id)`

So inserting the same mapping twice becomes a no-op (`ON CONFLICT DO NOTHING`), while still allowing multi-ticker events.

---

## 4) Signals (optional anti-dup)

Signals are intentionally appendable, but if you want to prevent duplicates you can enable the commented unique index in `postgres_schema.sql`:
- `(ticker_id, signal_type, signal_timestamp_utc, model_version)`

Use this only after you decide whether multiple identical timestamps are meaningful for your workflow.

