from __future__ import annotations

import argparse
import logging
from uuid import uuid4

from dotenv import load_dotenv

from .config import load_settings
from .db import connect, fetchall
from .checkpoints import get_checkpoint, set_checkpoint
from .runs import start_run, finish_run
from .storage import store_raw_document
from .registry import build_connectors
from .logging_utils import get_logger, log_json
from .models import RunStats


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")


def cmd_status(conn, connector: str | None):
    if connector:
        rows = fetchall(
            conn,
            "SELECT connector_name, last_cursor, last_since_utc, updated_at_utc FROM ingestion_checkpoints WHERE connector_name=%s",
            (connector,),
        )
    else:
        rows = fetchall(
            conn,
            "SELECT connector_name, last_cursor, last_since_utc, updated_at_utc FROM ingestion_checkpoints ORDER BY connector_name",
            (),
        )
    return rows


def run_connector(conn, connector_name: str, limit: int, dry_run: bool = False, validate_only: bool = False):
    settings = load_settings()
    connectors = build_connectors(settings)
    if connector_name not in connectors:
        raise SystemExit(f"Unknown connector: {connector_name}. Available: {', '.join(connectors.keys())}")

    logger = get_logger()
    stats = RunStats()
    run_id = str(uuid4())

    cp = get_checkpoint(conn, connector_name)
    log_json(logger, logging.INFO, "checkpoint_loaded", connector=connector_name, last_cursor=cp.last_cursor, last_since=str(cp.last_since_utc), meta=cp.meta)

    if not (dry_run or validate_only):
        start_run(conn, run_id, connector_name)

    try:
        connector = connectors[connector_name]
        records, new_cp = connector.fetch_batch(cp, limit=limit)

        stats.fetched += len(records)
        for rec in records:
            if dry_run or validate_only:
                continue
            _, inserted = store_raw_document(conn, rec, ingest_batch_id=run_id)
            if inserted:
                stats.stored += 1
            else:
                stats.deduped += 1

        if not (dry_run or validate_only):
            set_checkpoint(conn, new_cp)
            finish_run(conn, run_id, "SUCCESS", stats.__dict__, None)

        log_json(logger, logging.INFO, "run_complete", connector=connector_name, run_id=run_id, stats=stats.__dict__, dry_run=dry_run, validate_only=validate_only)
        return 0

    except Exception as e:
        stats.errors += 1
        if not (dry_run or validate_only):
            finish_run(conn, run_id, "FAILED", stats.__dict__, str(e))
        log_json(logger, logging.ERROR, "run_failed", connector=connector_name, run_id=run_id, error=str(e), stats=stats.__dict__)
        raise


def schedule_loop():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    settings = load_settings()
    logger = get_logger()

    sched = BlockingScheduler(timezone="UTC")

    def job(name: str, limit: int):
        with connect(settings.database_url) as conn:
            try:
                run_connector(conn, name, limit=limit)
            except Exception as e:
                log_json(logger, logging.ERROR, "scheduled_job_failed", connector=name, error=str(e))

    sched.add_job(lambda: job("sec_edgar", 120), IntervalTrigger(minutes=settings.sched_sec_minutes), id="sec_edgar")
    sched.add_job(lambda: job("usaspending_awards", 200), IntervalTrigger(minutes=settings.sched_usaspending_minutes), id="usaspending_awards")
    sched.add_job(lambda: job("dod_contracts", 40), IntervalTrigger(minutes=settings.sched_dod_minutes), id="dod_contracts")
    sched.add_job(lambda: job("politician_disclosures", 200), IntervalTrigger(minutes=settings.sched_politicians_minutes), id="politician_disclosures")

    log_json(
        logger,
        logging.INFO,
        "scheduler_started",
        schedules={
            "sec_edgar_minutes": settings.sched_sec_minutes,
            "usaspending_minutes": settings.sched_usaspending_minutes,
            "dod_minutes": settings.sched_dod_minutes,
            "politicians_minutes": settings.sched_politicians_minutes,
        },
    )
    sched.start()


def main(argv=None):
    load_dotenv(override=False)
    settings = load_settings()
    _configure_logging(settings.log_level)

    parser = argparse.ArgumentParser(prog="phase3_ingestion")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Ingestion commands")
    ingest_sub = ingest.add_subparsers(dest="ingest_cmd", required=True)

    runp = ingest_sub.add_parser("run", help="Run a connector once")
    runp.add_argument("connector", type=str)
    runp.add_argument("--limit", type=int, default=100)
    runp.add_argument("--dry-run", action="store_true")

    statp = ingest_sub.add_parser("status", help="Show checkpoints")
    statp.add_argument("connector", type=str, nargs="?", default=None)

    valp = ingest_sub.add_parser("validate", help="Fetch one batch and log only")
    valp.add_argument("connector", type=str)
    valp.add_argument("--limit", type=int, default=20)

    schp = ingest_sub.add_parser("schedule", help="Run APScheduler loop")

    args = parser.parse_args(argv)

    if args.ingest_cmd == "schedule":
        schedule_loop()
        return 0

    with connect(settings.database_url) as conn:
        if args.ingest_cmd == "status":
            rows = cmd_status(conn, args.connector)
            for r in rows:
                print(f"{r[0]}  cursor={r[1]}  since={r[2]}  updated={r[3]}")
            return 0

        if args.ingest_cmd == "validate":
            return run_connector(conn, args.connector, limit=args.limit, dry_run=True, validate_only=True)

        if args.ingest_cmd == "run":
            return run_connector(conn, args.connector, limit=args.limit, dry_run=args.dry_run, validate_only=False)

    return 0
