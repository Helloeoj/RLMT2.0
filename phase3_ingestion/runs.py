from __future__ import annotations

import json
from typing import Any, Optional

from .db import execute, fetchone

SQL_START = """
INSERT INTO ingestion_runs (run_id, connector_name, started_at_utc, status, stats_json)
VALUES (%s, %s, now(), 'RUNNING', '{}'::jsonb)
"""

SQL_FINISH = """
UPDATE ingestion_runs
SET ended_at_utc = now(),
    status = %s,
    stats_json = %s::jsonb,
    error_text = %s
WHERE run_id = %s
"""

SQL_LAST = """
SELECT run_id, connector_name, started_at_utc, ended_at_utc, status, stats_json, error_text
FROM ingestion_runs
WHERE connector_name = %s
ORDER BY started_at_utc DESC
LIMIT 1
"""


def start_run(conn: Any, run_id: str, connector_name: str) -> None:
    execute(conn, SQL_START, (run_id, connector_name))


def finish_run(conn: Any, run_id: str, status: str, stats: dict, error_text: str | None) -> None:
    execute(conn, SQL_FINISH, (status, json.dumps(stats, ensure_ascii=False), error_text, run_id))


def last_run(conn: Any, connector_name: str) -> Optional[tuple]:
    return fetchone(conn, SQL_LAST, (connector_name,))
