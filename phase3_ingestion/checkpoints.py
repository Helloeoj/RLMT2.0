from __future__ import annotations

import json
from typing import Any

from .db import fetchone, execute
from .models import Checkpoint

SQL_GET = """
SELECT connector_name, last_cursor, last_since_utc, etag, meta_json
FROM ingestion_checkpoints
WHERE connector_name = %s
"""

SQL_UPSERT = """
INSERT INTO ingestion_checkpoints (connector_name, last_cursor, last_since_utc, etag, meta_json, updated_at_utc)
VALUES (%s, %s, %s, %s, %s::jsonb, now())
ON CONFLICT (connector_name)
DO UPDATE SET
  last_cursor = EXCLUDED.last_cursor,
  last_since_utc = EXCLUDED.last_since_utc,
  etag = EXCLUDED.etag,
  meta_json = EXCLUDED.meta_json,
  updated_at_utc = now()
"""


def get_checkpoint(conn: Any, connector_name: str) -> Checkpoint:
    row = fetchone(conn, SQL_GET, (connector_name,))
    if not row:
        return Checkpoint(connector_name=connector_name)
    _, last_cursor, last_since_utc, etag, meta_json = row
    return Checkpoint(
        connector_name=connector_name,
        last_cursor=last_cursor,
        last_since_utc=last_since_utc,
        etag=etag,
        meta=meta_json or {},
    )


def set_checkpoint(conn: Any, cp: Checkpoint) -> None:
    execute(
        conn,
        SQL_UPSERT,
        (
            cp.connector_name,
            cp.last_cursor,
            cp.last_since_utc,
            cp.etag,
            json.dumps(cp.meta or {}, ensure_ascii=False),
        ),
    )
