from __future__ import annotations

import json
from typing import Any

from .models import RawRecord
from .utils import sha256_bytes

SQL_INSERT = """
INSERT INTO raw_documents (
  source_type, source_name, source_url, canonical_url,
  retrieved_at_utc, published_at_utc, title, mime_type,
  language, http_status, headers_json, raw_content, text_content,
  content_sha256, doc_fingerprint, ingest_batch_id, parse_status
)
VALUES (
  %s, %s, %s, %s,
  %s, %s, %s, %s,
  %s, %s, %s::jsonb, %s, %s,
  %s, %s, %s, 'RAW'
)
ON CONFLICT (doc_fingerprint) DO NOTHING
RETURNING raw_document_id
"""

def _doc_fingerprint(rec: RawRecord, content_sha: bytes) -> bytes:
    if rec.record_id:
        key = f"{rec.source_type}|{rec.source_name}|{rec.record_id}"
    elif rec.canonical_url:
        key = f"{rec.source_type}|{rec.source_name}|{rec.canonical_url}"
    else:
        key = f"{rec.source_type}|{rec.source_name}|{rec.url}|{content_sha.hex()}"
    return sha256_bytes(key.encode("utf-8"))

def store_raw_document(conn: Any, rec: RawRecord, ingest_batch_id: str) -> tuple[str | None, bool]:
    raw_bytes = rec.raw_bytes
    text = rec.text

    if raw_bytes is None and text is None:
        raise ValueError("RawRecord must include raw_bytes or text")

    if raw_bytes is None:
        raw_bytes = text.encode("utf-8")

    content_sha = sha256_bytes(raw_bytes)
    doc_fp = _doc_fingerprint(rec, content_sha)

    headers_json = {
        "record_id": rec.record_id,
        "meta": rec.meta or {},
        "resp_headers": rec.headers or {},
    }

    with conn.cursor() as cur:
        cur.execute(
            SQL_INSERT,
            (
                rec.source_type,
                rec.source_name,
                rec.url,
                rec.canonical_url,
                rec.fetched_at_utc,
                rec.published_at_utc,
                rec.title,
                rec.mime_type,
                (rec.meta or {}).get("language"),
                rec.http_status,
                json.dumps(headers_json, ensure_ascii=False),
                raw_bytes,
                text,
                content_sha,
                doc_fp,
                ingest_batch_id,
            ),
        )
        row = cur.fetchone()
        if row:
            return str(row[0]), True
        return None, False
