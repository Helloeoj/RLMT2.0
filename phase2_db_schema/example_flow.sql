\
-- Example flow: raw_document -> event -> score -> signal
-- NOTE: Values here are illustrative. Replace with your real ingest/parser outputs.

BEGIN;

-- 1) Insert an entity + ticker
INSERT INTO entities (entity_type, canonical_name, normalized_name)
VALUES ('COMPANY', 'Example Energy Corp', 'example energy corp')
ON CONFLICT (entity_type, normalized_name) DO UPDATE
SET canonical_name = EXCLUDED.canonical_name
RETURNING entity_id;

-- For simplicity: create ticker (use correct exchange/symbol)
WITH e AS (
  SELECT entity_id FROM entities WHERE entity_type='COMPANY' AND normalized_name='example energy corp'
)
INSERT INTO tickers (symbol, symbol_normalized, exchange, company_name, entity_id)
SELECT 'EXEN', 'EXEN', 'NASDAQ', 'Example Energy Corp', e.entity_id
FROM e
ON CONFLICT (exchange, symbol_normalized) DO UPDATE
SET company_name = EXCLUDED.company_name,
    entity_id = EXCLUDED.entity_id,
    last_seen_at_utc = now()
RETURNING ticker_id;

-- 2) Insert raw document
-- You compute these hashes in your ingest code. Here we just use dummy 32-byte values.
INSERT INTO raw_documents (
  source_type, source_name, source_url, canonical_url,
  retrieved_at_utc, published_at_utc, title,
  content_sha256, doc_fingerprint, parse_status
) VALUES (
  'REPUTABLE_MEDIA', 'ExampleWire', 'https://example.com/story/123', 'https://example.com/story/123',
  now(), now(), 'Example Energy wins a federal award',
  decode(repeat('aa',32),'hex'), decode(repeat('bb',32),'hex'), 'PARSED'
) RETURNING raw_document_id;

-- 3) Insert event and link it to the ticker
WITH rd AS (
  SELECT raw_document_id FROM raw_documents WHERE canonical_url='https://example.com/story/123' ORDER BY created_at_utc DESC LIMIT 1
),
t AS (
  SELECT ticker_id FROM tickers WHERE exchange='NASDAQ' AND symbol_normalized='EXEN'
)
INSERT INTO events (
  raw_document_id, event_type, title, summary,
  event_timestamp_utc, discovered_at_utc,
  source_type, source_name, source_url,
  source_hash, theme_tags, confidence,
  credibility_score, freshness_score, materiality_score, overall_score,
  details_json, event_fingerprint
)
SELECT
  rd.raw_document_id,
  'FED_AWARD',
  'Example Energy wins $50M federal award',
  'Award announced; details in the source document.',
  now(), now(),
  'REPUTABLE_MEDIA', 'ExampleWire', 'https://example.com/story/123',
  decode(repeat('cc',32),'hex'),
  ARRAY['military_contracts','energy'],
  'MEDIUM',
  80, 90, 70, 78,
  jsonb_build_object('award_id','ABC-123','amount_usd',50000000,'agency','Example Agency'),
  decode(repeat('dd',32),'hex')
FROM rd;

-- link
INSERT INTO event_ticker_links (event_id, ticker_id, link_role, map_confidence, map_method, map_rationale)
SELECT e.event_id, t.ticker_id, 'PRIMARY', 90, 'NAME_MATCH', 'Issuer matched to ticker entity'
FROM events e, t
WHERE e.source_url='https://example.com/story/123'
ON CONFLICT (event_id, ticker_id) DO NOTHING;

-- 4) Daily scores (normally computed)
WITH t AS (
  SELECT ticker_id FROM tickers WHERE exchange='NASDAQ' AND symbol_normalized='EXEN'
),
e AS (
  SELECT array_agg(event_id) AS evs FROM events WHERE source_url='https://example.com/story/123'
)
INSERT INTO scores_daily (
  ticker_id, as_of_date, model_version,
  score_total, score_freshness, score_materiality, score_theme_fit, score_source_credibility,
  top_event_ids, explain_json
)
SELECT
  t.ticker_id, CURRENT_DATE, 'score_v1',
  0.812, 0.900, 0.700, 0.850, 0.800,
  e.evs,
  jsonb_build_object('weights', jsonb_build_object('freshness',0.25,'materiality',0.35,'theme_fit',0.20,'credibility',0.20))
FROM t, e
ON CONFLICT (ticker_id, as_of_date, model_version) DO UPDATE
SET score_total = EXCLUDED.score_total,
    top_event_ids = EXCLUDED.top_event_ids,
    explain_json = EXCLUDED.explain_json;

-- 5) Emit a signal (watchlist add)
WITH t AS (
  SELECT ticker_id FROM tickers WHERE exchange='NASDAQ' AND symbol_normalized='EXEN'
),
e AS (
  SELECT array_agg(event_id) AS evs FROM events WHERE source_url='https://example.com/story/123'
),
s AS (
  SELECT score_total, score_freshness, score_materiality, score_theme_fit, score_source_credibility
  FROM scores_daily
  WHERE ticker_id = (SELECT ticker_id FROM t) AND as_of_date = CURRENT_DATE AND model_version='score_v1'
)
INSERT INTO signals (
  ticker_id, signal_timestamp_utc, signal_type, direction, strength, model_version,
  supporting_event_ids, score_snapshot, rationale, expires_at_utc
)
SELECT
  t.ticker_id, now(), 'WATCHLIST_ADD', 'NEUTRAL', 78.0, 'score_v1',
  e.evs,
  jsonb_build_object(
    'score_total', s.score_total,
    'freshness', s.score_freshness,
    'materiality', s.score_materiality,
    'theme_fit', s.score_theme_fit,
    'credibility', s.score_source_credibility
  ),
  'Score exceeded threshold; add to watchlist for monitoring.',
  now() + interval '7 days'
FROM t, e, s;

COMMIT;
