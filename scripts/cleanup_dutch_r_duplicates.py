#!/usr/bin/env python3
"""One-off: dedup 2026 Dutch GP race laps and fail zombie import jobs.

Requires ADC / GOOGLE_APPLICATION_CREDENTIALS for BigQuery.
DATABASE_URL is optional (skips job updates if unset).

    python3 scripts/cleanup_dutch_r_duplicates.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker" / "pipeline"))

from f1_telemetry_import import PROJECT, DATASET, generate_session_key  # noqa: E402
from google.cloud import bigquery  # noqa: E402

ZOMBIE_JOBS = (
    "c70cd3b7-97a3-4ade-ba0e-eb4acdf5541a",
    "b7fec1ec-e429-46eb-93be-a9023a93f476",
)
REASON = "Force-failed: Cloud Run timed out during streaming telemetry upload"


def dedup_laps() -> None:
    sk = generate_session_key(2026, "Dutch Grand Prix", "R")
    client = bigquery.Client(project=PROJECT)
    count_q = f"""
        SELECT COUNT(*) AS n,
               COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS uniq
        FROM `{PROJECT}.{DATASET}.laps`
        WHERE session_key = {sk}
    """
    before = list(client.query(count_q).result())[0]
    print(f"laps before: {before.n} rows, {before.uniq} unique driver/lap (session_key={sk})")

    sql_path = ROOT / "sql" / "dedup_dutch_2026_r_laps.sql"
    job = client.query(sql_path.read_text())
    job.result()
    print(f"delete job {job.job_id} affected={job.num_dml_affected_rows}")

    after = list(client.query(count_q).result())[0]
    print(f"laps after: {after.n} rows, {after.uniq} unique driver/lap")


def fail_zombies() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL unset — skip zombie job updates")
        return
    import psycopg2

    conn = psycopg2.connect(url)
    try:
        with conn:
            with conn.cursor() as cur:
                for job_id in ZOMBIE_JOBS:
                    cur.execute(
                        """
                        UPDATE jobs
                        SET status = 'failed',
                            finished_at = COALESCE(finished_at, now()),
                            error = %s,
                            status_message = %s,
                            updated_at = now()
                        WHERE id = %s AND status IN ('queued', 'running', 'cancelling')
                        RETURNING id, status
                        """,
                        (REASON, REASON, job_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        print(f"job {job_id}: not fail-able (missing or already terminal)")
                        continue
                    cur.execute(
                        """
                        UPDATE job_steps
                        SET status = 'failed',
                            finished_at = COALESCE(finished_at, now()),
                            message = COALESCE(message, %s)
                        WHERE job_id = %s AND status IN ('pending', 'running')
                        """,
                        (REASON, job_id),
                    )
                    cur.execute(
                        "INSERT INTO job_logs (job_id, level, message) VALUES (%s, 'error', %s)",
                        (job_id, REASON),
                    )
                    print(f"job {job_id}: marked failed")
    finally:
        conn.close()


if __name__ == "__main__":
    dedup_laps()
    fail_zombies()
