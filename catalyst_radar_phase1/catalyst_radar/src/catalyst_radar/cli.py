from __future__ import annotations

import argparse
from pathlib import Path

from catalyst_radar.config.logging import setup_logging
from catalyst_radar.config.settings import Settings
from catalyst_radar.pipeline.runner import PipelineRunner


def _default_fixtures_path() -> str:
    # Default assumes you run from repo root.
    return str(Path("data") / "fixtures" / "stub_events.json")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="catalyst_radar")
    sub = parser.add_subparsers(dest="cmd", required=True)

    hello = sub.add_parser("hello", help="Run end-to-end pipeline with stub fixtures")
    hello.add_argument("--fixtures", default=_default_fixtures_path(), help="Path to stub fixture JSON")

    args = parser.parse_args(argv)
    settings = Settings()
    setup_logging(settings.log_level)

    if args.cmd == "hello":
        runner = PipelineRunner(settings=settings, fixtures_path=args.fixtures)
        result = runner.run()
        print("OK")
        print(f"events_seen: {result.events_seen}")
        print(f"events_new: {result.events_new}")
        print(f"watchlist_count: {result.watchlist_count}")
        print(f"ledger_path: {result.ledger_path}")
        print(f"watchlist_path: {result.watchlist_path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
