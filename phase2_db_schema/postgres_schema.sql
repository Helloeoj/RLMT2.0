\
-- Phase 2 Schema (PostgreSQL 16+)
-- Storage design only. No broker execution. No UI.

BEGIN;

-- Extensions (safe to keep even if unused today)
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- optional fuzzy name matching later

-- =========================
-- ENUM-like CHECK helpers
-- =========================

-- raw_documents.parse_status: RAW|PARSED|FAILED
-- events.confidence: LOW|MEDIUM|HIGH
-- signals.status: ACTIVE|EXPIRED|CANCELLED
-- signals.direction: LONG|SHORT|NEUTRAL
-- entities.entity_type: COMPANY|PERSON|AGENCY|COMMODITY|PROJECT|REGION|OTHER
-- event_ticker_links.link_role: PRIMARY|SECONDARY|INDUSTRY_BASKET

-- =========================
-- raw_documents
-- =========================
CREATE TABLE IF NOT EXISTS raw_documents (
  raw_document_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type          TEXT NOT NULL,
  source_name          TEXT NOT NULL,
  source_url           TEXT NOT NULL,
  canonical_url        TEXT,
  retrieved_at_utc     TIMESTAMPTZ NOT NULL,
  published_at_utc     TIMESTAMPTZ,
  title                TEXT,
  mime_type            TEXT,
  language             TEXT,
  http_status          INT,
  headers_json         JSONB,
  raw_content          BYTEA,
  text_content         TEXT,
  content_sha256       BYTEA NOT NULL CHECK (octet_length(content_sha256) = 32),
  doc_fingerprint      BYTEA NOT NULL CHECK (octet_length(doc_fingerprint) = 32),
  ingest_batch_id      UUID,
  parse_status         TEXT NOT NULL DEFAULT 'RAW' CHECK (parse_status IN ('RAW','PARSED','FAILED')),
  parse_error          TEXT,
  created_at_utc       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_documents_doc_fingerprint
  ON raw_documents (doc_fingerprint);

CREATE INDEX IF NOT EXISTS ix_raw_documents_retrieved_at
  ON raw_documents (retrieved_at_utc DESC);

CREATE INDEX IF NOT EXISTS ix_raw_documents_published_at
  ON raw_documents (published_at_utc DESC);

CREATE INDEX IF NOT EXISTS ix_raw_documents_source
  ON raw_documents (source_type, source_name);

CREATE INDEX IF NOT EXISTS ix_raw_documents_canonical_url
  ON raw_documents (canonical_url);


-- =========================
-- entities
-- =========================
CREATE TABLE IF NOT EXISTS entities (
  entity_id            BIGSERIAL PRIMARY KEY,
  entity_type          TEXT NOT NULL CHECK (entity_type IN ('COMPANY','PERSON','AGENCY','COMMODITY','PROJECT','REGION','OTHER')),
  canonical_name       TEXT NOT NULL,
  normalized_name      TEXT NOT NULL,
  aliases              JSONB,
  country_code         TEXT,
  external_ids         JSONB,
  created_at_utc       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_entities_type_normname
  ON entities (entity_type, normalized_name);

CREATE INDEX IF NOT EXISTS ix_entities_canonical_name
  ON entities (canonical_name);

-- Optional fuzzy search support (requires pg_trgm; already enabled above)
CREATE INDEX IF NOT EXISTS ix_entities_canonical_name_trgm
  ON entities USING GIN (canonical_name gin_trgm_ops);


-- =========================
-- tickers
-- =========================
CREATE TABLE IF NOT EXISTS tickers (
  ticker_id            BIGSERIAL PRIMARY KEY,
  symbol               TEXT NOT NULL,
  symbol_normalized    TEXT NOT NULL,
  exchange             TEXT NOT NULL,
  security_type        TEXT NOT NULL DEFAULT 'COMMON_STOCK',
  company_name         TEXT NOT NULL,
  entity_id            BIGINT REFERENCES entities(entity_id),
  cik                  TEXT,
  isin                 TEXT,
  cusip                TEXT,
  sector               TEXT,
  industry             TEXT,
  is_active            BOOLEAN NOT NULL DEFAULT TRUE,
  first_seen_at_utc    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at_utc     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tickers_exchange_symbol
  ON tickers (exchange, symbol_normalized);

CREATE INDEX IF NOT EXISTS ix_tickers_symbol
  ON tickers (symbol_normalized);

CREATE INDEX IF NOT EXISTS ix_tickers_entity_id
  ON tickers (entity_id);

CREATE INDEX IF NOT EXISTS ix_tickers_active
  ON tickers (is_active) WHERE is_active = TRUE;


-- Identifier indexes (useful for deterministic ticker resolution)
CREATE INDEX IF NOT EXISTS ix_tickers_cik
  ON tickers (cik);

CREATE INDEX IF NOT EXISTS ix_tickers_isin
  ON tickers (isin);

CREATE INDEX IF NOT EXISTS ix_tickers_cusip
  ON tickers (cusip);


-- =========================
-- events
-- =========================
CREATE TABLE IF NOT EXISTS events (
  event_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_document_id        UUID REFERENCES raw_documents(raw_document_id),
  event_type             TEXT NOT NULL,
  title                  TEXT NOT NULL,
  summary                TEXT NOT NULL,
  event_timestamp_utc    TIMESTAMPTZ NOT NULL,
  discovered_at_utc      TIMESTAMPTZ NOT NULL,
  source_type            TEXT NOT NULL,
  source_name            TEXT NOT NULL,
  source_url             TEXT NOT NULL,
  source_hash            BYTEA NOT NULL CHECK (octet_length(source_hash) = 32),
  corroborating_sources  JSONB,
  theme_tags             TEXT[] NOT NULL DEFAULT '{}'::text[],
  confidence             TEXT NOT NULL CHECK (confidence IN ('LOW','MEDIUM','HIGH')),
  credibility_score      SMALLINT NOT NULL CHECK (credibility_score BETWEEN 0 AND 100),
  freshness_score        SMALLINT NOT NULL CHECK (freshness_score BETWEEN 0 AND 100),
  materiality_score      SMALLINT NOT NULL CHECK (materiality_score BETWEEN 0 AND 100),
  overall_score          SMALLINT NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  details_json           JSONB,
  ambiguity_notes        TEXT,
  event_fingerprint      BYTEA NOT NULL CHECK (octet_length(event_fingerprint) = 32),
  version                INT NOT NULL DEFAULT 1 CHECK (version >= 1),
  supersedes_event_id    UUID REFERENCES events(event_id),
  is_suppressed          BOOLEAN NOT NULL DEFAULT FALSE,
  created_at_utc         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_events_event_fingerprint
  ON events (event_fingerprint);

CREATE INDEX IF NOT EXISTS ix_events_event_time
  ON events (event_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS ix_events_discovered_time
  ON events (discovered_at_utc DESC);

CREATE INDEX IF NOT EXISTS ix_events_type_time
  ON events (event_type, event_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS ix_events_score_time
  ON events (overall_score DESC, event_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS ix_events_not_suppressed
  ON events (event_timestamp_utc DESC) WHERE is_suppressed = FALSE;

CREATE INDEX IF NOT EXISTS ix_events_theme_tags
  ON events USING GIN (theme_tags);

CREATE INDEX IF NOT EXISTS ix_events_details_json
  ON events USING GIN (details_json);


-- =========================
-- event_ticker_links
-- =========================
CREATE TABLE IF NOT EXISTS event_ticker_links (
  event_id           UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  ticker_id          BIGINT NOT NULL REFERENCES tickers(ticker_id),
  link_role          TEXT NOT NULL DEFAULT 'PRIMARY' CHECK (link_role IN ('PRIMARY','SECONDARY','INDUSTRY_BASKET')),
  map_confidence     SMALLINT NOT NULL CHECK (map_confidence BETWEEN 0 AND 100),
  map_method         TEXT NOT NULL,
  map_rationale      TEXT,
  created_at_utc     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (event_id, ticker_id)
);

CREATE INDEX IF NOT EXISTS ix_event_ticker_links_ticker_event
  ON event_ticker_links (ticker_id, event_id);

CREATE INDEX IF NOT EXISTS ix_event_ticker_links_ticker_confidence
  ON event_ticker_links (ticker_id, map_confidence DESC);



-- =========================
-- Phase 5 Extensions: ticker_aliases + review_queue (additive)
-- =========================

-- Aliases curated by humans (fast path for Tier 2 exact alias match)
CREATE TABLE IF NOT EXISTS ticker_aliases (
  alias_normalized      TEXT PRIMARY KEY,
  ticker_id             BIGINT NOT NULL REFERENCES tickers(ticker_id),
  source                TEXT,
  confidence            SMALLINT CHECK (confidence BETWEEN 0 AND 100),
  evidence_json         JSONB,
  added_by              TEXT,
  added_at_utc          TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_validated_at_utc TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_ticker_aliases_ticker_id
  ON ticker_aliases (ticker_id);

CREATE INDEX IF NOT EXISTS ix_ticker_aliases_source
  ON ticker_aliases (source);

-- Manual review queue for ambiguous resolutions (Phase 5 Tier 5)
CREATE TABLE IF NOT EXISTS review_queue (
  queue_id           BIGSERIAL PRIMARY KEY,
  event_id           UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  payload_json       JSONB NOT NULL,
  status             TEXT NOT NULL DEFAULT 'needs_human_decision'
                     CHECK (status IN ('needs_human_decision','resolved','dismissed')),
  created_at_utc     TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at_utc    TIMESTAMPTZ,
  reviewer           TEXT,
  resolution         JSONB
);

-- Common lookups
CREATE INDEX IF NOT EXISTS ix_review_queue_status_created
  ON review_queue (status, created_at_utc DESC);

CREATE INDEX IF NOT EXISTS ix_review_queue_event_id
  ON review_queue (event_id);

-- Only one active pending item per event
CREATE UNIQUE INDEX IF NOT EXISTS ux_review_queue_event_pending
  ON review_queue (event_id)
  WHERE status = 'needs_human_decision';

-- =========================
-- features_daily
-- =========================
CREATE TABLE IF NOT EXISTS features_daily (
  ticker_id             BIGINT NOT NULL REFERENCES tickers(ticker_id),
  as_of_date            DATE NOT NULL,
  feature_set_version   TEXT NOT NULL,
  close                 NUMERIC(18,6),
  volume                BIGINT,
  dollar_volume         NUMERIC(18,2),
  addv_20d              NUMERIC(18,2),
  market_cap            NUMERIC(18,2),
  pct_change_1d         NUMERIC(9,6),
  pct_change_5d         NUMERIC(9,6),
  volatility_20d        NUMERIC(9,6),
  features_json         JSONB,
  created_at_utc        TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker_id, as_of_date, feature_set_version)
);

CREATE INDEX IF NOT EXISTS ix_features_daily_date_ticker
  ON features_daily (as_of_date, ticker_id);


-- =========================
-- scores_daily
-- =========================
CREATE TABLE IF NOT EXISTS scores_daily (
  ticker_id                BIGINT NOT NULL REFERENCES tickers(ticker_id),
  as_of_date               DATE NOT NULL,
  model_version            TEXT NOT NULL,
  score_total              NUMERIC(6,3) NOT NULL,
  score_freshness          NUMERIC(6,3) NOT NULL,
  score_materiality        NUMERIC(6,3) NOT NULL,
  score_theme_fit          NUMERIC(6,3) NOT NULL,
  score_source_credibility NUMERIC(6,3) NOT NULL,
  score_derisking          NUMERIC(6,3),
  top_event_ids            UUID[],
  explain_json             JSONB,
  created_at_utc           TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker_id, as_of_date, model_version)
);

CREATE INDEX IF NOT EXISTS ix_scores_daily_date_score
  ON scores_daily (as_of_date, score_total DESC);

CREATE INDEX IF NOT EXISTS ix_scores_daily_ticker_date
  ON scores_daily (ticker_id, as_of_date DESC);


-- =========================
-- signals
-- =========================
CREATE TABLE IF NOT EXISTS signals (
  signal_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker_id              BIGINT NOT NULL REFERENCES tickers(ticker_id),
  signal_timestamp_utc   TIMESTAMPTZ NOT NULL,
  signal_type            TEXT NOT NULL,
  direction              TEXT NOT NULL DEFAULT 'NEUTRAL' CHECK (direction IN ('LONG','SHORT','NEUTRAL')),
  strength               NUMERIC(6,3) NOT NULL,
  model_version          TEXT NOT NULL,
  supporting_event_ids   UUID[],
  score_snapshot         JSONB,
  rationale              TEXT NOT NULL,
  expires_at_utc         TIMESTAMPTZ,
  status                 TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','EXPIRED','CANCELLED')),
  created_at_utc         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_signals_ticker_time
  ON signals (ticker_id, signal_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS ix_signals_type_time
  ON signals (signal_type, signal_timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS ix_signals_active
  ON signals (status, expires_at_utc) WHERE status = 'ACTIVE';

-- Optional anti-dup (comment out if you want multiple identical timestamps):
-- CREATE UNIQUE INDEX IF NOT EXISTS ux_signals_nodup
--   ON signals (ticker_id, signal_type, signal_timestamp_utc, model_version);


-- =========================
-- FUTURE: orders, fills, positions (defined but not used)
-- =========================
CREATE TABLE IF NOT EXISTS orders (
  order_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at_utc      TIMESTAMPTZ NOT NULL DEFAULT now(),
  strategy_id         TEXT NOT NULL,
  ticker_id           BIGINT NOT NULL REFERENCES tickers(ticker_id),
  side                TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
  order_type          TEXT NOT NULL,
  qty                 NUMERIC(18,6) NOT NULL,
  limit_price         NUMERIC(18,6),
  time_in_force       TEXT NOT NULL,
  status              TEXT NOT NULL,
  broker_ref          TEXT,
  meta_json           JSONB
);

CREATE TABLE IF NOT EXISTS fills (
  fill_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id            UUID NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  filled_at_utc       TIMESTAMPTZ NOT NULL,
  qty                 NUMERIC(18,6) NOT NULL,
  price               NUMERIC(18,6) NOT NULL,
  fee                 NUMERIC(18,6),
  liquidity_flag      TEXT,
  broker_ref          TEXT
);

CREATE TABLE IF NOT EXISTS positions (
  position_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  as_of_utc            TIMESTAMPTZ NOT NULL,
  ticker_id            BIGINT NOT NULL REFERENCES tickers(ticker_id),
  qty                  NUMERIC(18,6) NOT NULL,
  avg_cost             NUMERIC(18,6) NOT NULL,
  unrealized_pnl       NUMERIC(18,6),
  realized_pnl         NUMERIC(18,6),
  meta_json            JSONB
);

COMMIT;
