# Catalyst Radar (Phase 1 Skeleton)

This repo is the **Phase 1 architecture skeleton** for a private, public-data-only "Catalyst Radar".

**Scope limits (Phase 1):**
- No UI
- No live trading / broker execution
- No real network connectors (stubs + local fixtures only)

## Quickstart

### 1) Requirements
- Python 3.10+

### 2) Run the hello pipeline
From the repo root:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate

python -m pip install -e .
python -m catalyst_radar.cli hello
```

Outputs will be written to:
- `out/event_ledger.jsonl`
- `out/watchlist.json`

### 3) Run tests
```bash
python -m unittest -v
```

## Notes
- All logic, fields, and gates are derived from **phase0.txt** (source of truth).
- Any missing numeric thresholds or scoring formulas are explicitly marked **TBD**.
