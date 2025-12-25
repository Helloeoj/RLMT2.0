from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Iterable, Optional

from .normalize import normalize_raw_document


def _read_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def _write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 4 normalization (raw_documents -> canonical events)")
    ap.add_argument("--input-jsonl", help="JSONL file containing raw_document-like rows")
    ap.add_argument("--output-jsonl", default="phase4_normalization\\out_events.jsonl", help="Where to write events JSONL")
    ap.add_argument("--quarantine-jsonl", default="phase4_normalization\\out_quarantine.jsonl", help="Where to write quarantined rows")
    ap.add_argument("--reject-jsonl", default="phase4_normalization\\out_reject.jsonl", help="Where to write rejected rows")
    args = ap.parse_args()

    if not args.input_jsonl:
        print("ERROR: For now, use file mode. Example:\n  python -m phase4_normalization.cli --input-jsonl phase4_normalization\\sample_raw_documents.jsonl")
        return 2

    ok_events = []
    quarantine = []
    reject = []

    for raw in _read_jsonl(args.input_jsonl):
        res = normalize_raw_document(raw)
        if res.status == "ok" and res.event:
            ok_events.append(res.event)
        elif res.status == "quarantine":
            quarantine.append({"reason": res.reason, "raw": raw})
        else:
            reject.append({"reason": res.reason, "raw": raw})

    n_ok = _write_jsonl(args.output_jsonl, ok_events)
    n_q = _write_jsonl(args.quarantine_jsonl, quarantine)
    n_r = _write_jsonl(args.reject_jsonl, reject)

    print(f"OK events: {n_ok}")
    print(f"Quarantined: {n_q}")
    print(f"Rejected: {n_r}")
    print(f"Wrote: {args.output_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
