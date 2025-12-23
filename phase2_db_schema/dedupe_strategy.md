# Dedupe Strategy (Phase 2)

## Raw Document Dedupe (two-layer)
1) Canonicalize URL -> `canonical_url`
   - Normalize scheme/host casing
   - Remove tracking params (utm_*, fbclid, gclid, etc.)
   - Normalize trailing slashes

2) Content Hash -> `content_sha256`
   - SHA-256 of raw bytes OR normalized extracted text (pick one convention and stick to it)

3) Document Fingerprint -> `doc_fingerprint` (UNIQUE)
   Recommended identity string:
   `source_type | source_name | canonical_url | published_at_utc_bucket | content_sha256`
   Then SHA-256 that UTF-8 string.

`published_at_utc_bucket` can be:
- exact timestamp if the source is stable, OR
- date bucket (YYYY-MM-DD) to reduce false negatives when source timestamps are noisy

## Event Dedupe (hard key)
`event_fingerprint` (UNIQUE) should represent the underlying real-world event.

Recommended identity string:
`event_type | primary_identifier | event_timestamp_bucket | key_fields`
Then SHA-256.

Primary identifiers by event_type:
- FED_AWARD: award_id / contract_number, else agency+vendor+amount+PoP dates
- POLITICIAN_DISCLOSURE: person+tx_date+asset/ticker+tx_type+amount_band
- GEOPOLITICS_NEWS: action+region+effective_date+(official vs media)
- PREOP_MILESTONE: project+milestone_type+announced_date

Event timestamp bucket:
- often 1 hour buckets to catch reposts without merging distinct days
