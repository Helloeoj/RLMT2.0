-- Phase 5 (Ticker Resolution) - supporting tables
-- Safe to run multiple times.

-- Aliases curated by humans (fast path for Tier 2 exact alias match)
CREATE TABLE IF NOT EXISTS ticker_aliases (
  alias_normalized   TEXT PRIMARY KEY,
  ticker_id          BIGINT NOT NULL REFERENCES tickers(ticker_id),
  source             TEXT,
  confidence         SMALLINT CHECK (confidence BETWEEN 0 AND 100),
  evidence_json      JSONB,
  added_by           TEXT,
  added_at_utc       TIMESTAMPTZ NOT NULL DEFAULT now(),
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
