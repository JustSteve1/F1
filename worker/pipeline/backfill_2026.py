#!/usr/bin/env python3
"""Import 2026 sessions that have no lap rows, one event at a time.

A session that already has rows in ``laps`` or ``laps_live`` is left alone.
Live sessions stay on the live source. This script does not upload to Kaggle.

Auth is the interval subscription token or F1_USERNAME / F1_PASSWORD.
The token is never printed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))

from fastf1_auth import configure_fastf1_auth  # noqa: E402
from fastf1_schedule import build_schedule  # noqa: E402
from f1_telemetry_import import check_existing  # noqa: E402

YEAR = 2026

# Recent finished weekends first, then empty weekends, then sessions that
# have telemetry but no laps, then the missing codes on partial weekends.
EVENT_ORDER = [
    "Las Vegas Grand Prix",
    "São Paulo Grand Prix",
    "Mexico City Grand Prix",
    "Barcelona Grand Prix",
    "Austrian Grand Prix",
    "Belgian Grand Prix",
    "Hungarian Grand Prix",
    "Azerbaijan Grand Prix",
    "Bahrain Grand Prix",
    "Australian Grand Prix",
    "Japanese Grand Prix",
    "Chinese Grand Prix",
    "Canadian Grand Prix",
    "Spanish Grand Prix",
    "Miami Grand Prix",
    "British Grand Prix",
    "Dutch Grand Prix",
    "Italian Grand Prix",
    "Singapore Grand Prix",
]


def order_events(names: list[str]) -> list[str]:
    rank = {name: index for index, name in enumerate(EVENT_ORDER)}
    return sorted(names, key=lambda name: (rank.get(name, len(EVENT_ORDER)), name))


def due_session_codes(sessions: list[dict], now: datetime) -> list[str]:
    """Session codes whose start time is already in the past."""
    codes = []
    for session in sessions:
        raw = session.get("dateUtc")
        code = session.get("code")
        if not raw or not code:
            continue
        start = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start <= now:
            codes.append(code)
    return codes


def sessions_to_import(scheduled: list[str], present: set[str]) -> list[str]:
    return [code for code in scheduled if code not in present]


def _ensure_gcp_credentials() -> None:
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    raw = os.environ.get("GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY")
    if not raw:
        return
    path = Path("/tmp/gcp-bootstrap-sa.json")
    path.write_text(raw, encoding="utf-8")
    path.chmod(0o600)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(path)


def _quality(client, event_name: str) -> None:
    from google.cloud import bigquery

    project = os.environ.get("BQ_PROJECT", "f1-data-library")
    dataset = os.environ.get("BQ_DATASET", "f1_data_library_DS")
    query = f"""
        SELECT
          session_type,
          COUNT(*) AS laps,
          COUNT(DISTINCT driver_number) AS drivers,
          MIN(lap_duration) AS min_sec,
          MAX(lap_duration) AS max_sec
        FROM `{project}.{dataset}.laps`
        WHERE season = {YEAR} AND event_name = @event
        GROUP BY session_type
        ORDER BY session_type
    """
    job = client.query(
        query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("event", "STRING", event_name)]
        ),
    )
    frame = job.to_dataframe()
    print(f"  quality {event_name}:")
    if frame.empty:
        print("    no batch lap rows")
        return
    for _, row in frame.iterrows():
        print(
            f"    {row['session_type']}: laps={int(row['laps'])} "
            f"drivers={int(row['drivers'])} "
            f"lap_sec=({row['min_sec']}, {row['max_sec']})"
        )


def run_backfill(*, dry_run: bool = False, now: datetime | None = None) -> int:
    auth = configure_fastf1_auth()
    print(f"FastF1 auth: {auth}")
    if auth == "missing":
        print(
            "Cannot import. The F1 bearer is not on this machine. "
            "Put it in ~/.config/interval/f1-subscription-token "
            "or set F1_USERNAME and F1_PASSWORD."
        )

    now = now or datetime.now(timezone.utc)
    schedule = build_schedule(YEAR)
    by_name = {event["eventName"]: event for event in schedule["events"]}
    wanted = [name for name in order_events(list(by_name)) if name in EVENT_ORDER]

    _ensure_gcp_credentials()
    from google.cloud import bigquery

    client = bigquery.Client(project=os.environ.get("BQ_PROJECT", "f1-data-library"))

    for event_name in wanted:
        event = by_name[event_name]
        scheduled = due_session_codes(event["sessions"], now)
        if not scheduled:
            print(f"skip {event_name}: no sessions have started")
            continue
        present_keys = check_existing(client, [YEAR], event_name, scheduled)
        present = {stype for year, stype in present_keys if year == YEAR}
        missing = sessions_to_import(scheduled, present)
        if not missing:
            print(f"skip {event_name}: lap rows already stored for {scheduled}")
            continue
        print(f"import {event_name}: {missing}")
        if dry_run or auth == "missing":
            continue
        command = [
            sys.executable,
            str(PIPELINE / "f1_telemetry_import.py"),
            "--year",
            str(YEAR),
            "--race",
            event_name,
            "--session",
            *missing,
        ]
        completed = subprocess.run(command, cwd=PIPELINE, check=False)
        if completed.returncode != 0:
            print(f"stopped after {event_name}: importer exit {completed.returncode}")
            return completed.returncode
        _quality(client, event_name)
    return 2 if auth == "missing" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill missing 2026 lap rows")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sessions that would be imported",
    )
    args = parser.parse_args(argv)
    return run_backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
