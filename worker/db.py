"""Postgres helpers for the Cloud Run Jobs worker."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
import psycopg2.extras

from job_control import status_guard_sql


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return psycopg2.connect(url)


@contextmanager
def cursor() -> Iterator[Any]:
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def get_job(job_id: str) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def append_log(job_id: str, message: str, level: str = "info") -> None:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO job_logs (job_id, level, message) VALUES (%s, %s, %s)",
            (job_id, level, message),
        )


def _status_guard_sql(status: str | None) -> str:
    """Back-compat alias for tests / callers."""
    return status_guard_sql(status)


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress_pct: float | None = None,
    current_step: str | None = None,
    status_message: str | None = None,
    error: str | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    fields: list[str] = ["updated_at = now()"]
    values: list[Any] = []

    if status is not None:
        fields.append("status = %s")
        values.append(status)
    if progress_pct is not None:
        fields.append("progress_pct = %s")
        values.append(progress_pct)
    if current_step is not None:
        fields.append("current_step = %s")
        values.append(current_step)
    if status_message is not None:
        fields.append("status_message = %s")
        values.append(status_message)
    if error is not None:
        fields.append("error = %s")
        values.append(error)
    if started:
        fields.append("started_at = COALESCE(started_at, now())")
    if finished:
        fields.append("finished_at = now()")

    values.append(job_id)
    extra = status_guard_sql(status)
    with cursor() as cur:
        cur.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE id = %s{extra}",
            values,
        )


def heartbeat(job_id: str) -> None:
    """Touch updated_at so the admin UI/watchdog knows the worker is alive."""
    with cursor() as cur:
        cur.execute(
            """
            UPDATE jobs
            SET updated_at = now()
            WHERE id = %s AND status IN ('queued', 'running', 'cancelling')
            """,
            (job_id,),
        )


def begin_step(job_id: str, step_key: str, message: str) -> None:
    with cursor() as cur:
        cur.execute(
            """
            UPDATE job_steps
            SET status = 'running', started_at = now(), message = %s
            WHERE job_id = %s AND step_key = %s
            """,
            (message, job_id, step_key),
        )


def finish_step(
    job_id: str,
    step_key: str,
    status: str,
    message: str | None = None,
) -> None:
    with cursor() as cur:
        cur.execute(
            """
            UPDATE job_steps
            SET status = %s, finished_at = now(), message = COALESCE(%s, message)
            WHERE job_id = %s AND step_key = %s
            """,
            (status, message, job_id, step_key),
        )


def job_status(job_id: str) -> str | None:
    with cursor() as cur:
        cur.execute("SELECT status FROM jobs WHERE id = %s", (job_id,))
        row = cur.fetchone()
        return str(row["status"]) if row else None


def is_cancelling(job_id: str) -> bool:
    return job_status(job_id) == "cancelling"


def should_stop(job_id: str) -> bool:
    return job_status(job_id) in ("cancelling", "cancelled", "failed")
