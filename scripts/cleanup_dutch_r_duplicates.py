#!/usr/bin/env python3
"""Preview or apply 2026 Dutch GP race laps dedup.

Requires ADC / GOOGLE_APPLICATION_CREDENTIALS for BigQuery.

    python3 scripts/cleanup_dutch_r_duplicates.py           # preview
    python3 scripts/cleanup_dutch_r_duplicates.py --apply   # rewrite laps
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker" / "pipeline"))

from f1_telemetry_import import PROJECT, DATASET, generate_session_key  # noqa: E402
from google.cloud import bigquery  # noqa: E402

SK = generate_session_key(2026, "Dutch Grand Prix", "R")


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def _print_rows(job: bigquery.QueryJob) -> None:
    rows = list(job.result())
    if not rows:
        print("(no rows)")
        return
    keys = list(rows[0].keys())
    widths = {k: max(len(k), *(len(str(r[k])) for r in rows)) for k in keys}
    print("  ".join(k.ljust(widths[k]) for k in keys))
    for r in rows:
        print("  ".join(str(r[k]).ljust(widths[k]) for k in keys))


def preview() -> None:
    client = _client()
    print(f"Preview laps/telemetry/sessions for session_key={SK}")
    sql = (ROOT / "sql" / "preview_dutch_2026_r.sql").read_text()
    # The preview file has two statements; run as a script.
    job = client.query(sql)
    # First result (summary)
    _print_rows(job)
    try:
        while job.next_result():
            print()
            _print_rows(job)
    except AttributeError:
        pass


def apply() -> None:
    client = _client()
    sql = (ROOT / "sql" / "dedup_dutch_2026_r_laps.sql").read_text()
    print(f"Applying Dutch R laps dedup (session_key={SK})")
    job = client.query(sql)
    job.result()
    print(f"script job {job.job_id} affected={job.num_dml_affected_rows}")
    _print_rows(job)
    try:
        while job.next_result():
            print()
            _print_rows(job)
    except AttributeError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete extra Dutch R lap copies (default is preview only)",
    )
    args = parser.parse_args()
    print(f"project={PROJECT} dataset={DATASET} session_key={SK}")
    if args.apply:
        apply()
    else:
        preview()
        print("\nRe-run with --apply to delete extra copies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
