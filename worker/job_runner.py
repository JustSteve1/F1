"""
Orchestrates the F1 telemetry import pipeline for a single JOB_ID,
emitting step progress / logs into Postgres.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

# Ensure pipeline package is importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "pipeline"))

import db  # noqa: E402

STEP_ORDER = [
    "load_fastf1",
    "resample_telemetry",
    "upload_sessions_laps",
    "upload_telemetry",
    "verify",
    "quality_checks",
    "laps_unified",
    "kaggle_upload",
    "done",
]


def _params(job: dict[str, Any]) -> dict[str, Any]:
    p = job.get("params") or {}
    if isinstance(p, str):
        import json

        p = json.loads(p)
    return p


def _active_steps(params: dict[str, Any]) -> list[str]:
    steps = list(STEP_ORDER)
    if params.get("skipQuality"):
        steps = [s for s in steps if s != "quality_checks"]
    if params.get("skipUnified"):
        steps = [s for s in steps if s != "laps_unified"]
    if not params.get("includeKaggle"):
        steps = [s for s in steps if s != "kaggle_upload"]
    return steps


def _progress(step_key: str, params: dict[str, Any]) -> float:
    steps = _active_steps(params)
    if step_key == "done":
        return 100.0
    try:
        idx = steps.index(step_key)
    except ValueError:
        return 0.0
    return round((idx / max(len(steps) - 1, 1)) * 1000) / 10


def _run_step(
    job_id: str,
    params: dict[str, Any],
    step_key: str,
    label: str,
    fn: Callable[[], None],
) -> bool:
    """Returns False if cancelled before/during step."""
    if db.is_cancelling(job_id):
        return False

    db.begin_step(job_id, step_key, label)
    db.update_job(
        job_id,
        current_step=step_key,
        progress_pct=_progress(step_key, params),
        status_message=f"Running: {label}",
    )
    db.append_log(job_id, f"▶ {label}")

    try:
        fn()
        if db.is_cancelling(job_id):
            db.finish_step(job_id, step_key, "cancelled", "Cancelled")
            return False
        db.finish_step(job_id, step_key, "succeeded", f"{label} complete")
        db.append_log(job_id, f"✔ {label} complete")
        return True
    except Exception as exc:
        msg = f"{label} failed: {exc}"
        db.finish_step(job_id, step_key, "failed", msg)
        db.append_log(job_id, msg, level="error")
        db.append_log(job_id, traceback.format_exc(), level="error")
        raise


def _mark_cancelled(job_id: str, params: dict[str, Any], at_step: str) -> None:
    db.update_job(
        job_id,
        status="cancelled",
        finished=True,
        current_step=at_step,
        progress_pct=_progress(at_step, params),
        status_message="Cancelled",
    )
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE job_steps
            SET status = 'cancelled', finished_at = now(), message = 'Cancelled'
            WHERE job_id = %s AND status IN ('pending', 'running')
            """,
            (job_id,),
        )
    db.append_log(job_id, "Job cancelled", level="warn")


def _dry_run(job_id: str, params: dict[str, Any]) -> None:
    import time

    for step in _active_steps(params):
        label = step.replace("_", " ")
        ok = _run_step(job_id, params, step, label, lambda: time.sleep(0.4))
        if not ok:
            _mark_cancelled(job_id, params, step)
            return

    db.update_job(
        job_id,
        status="succeeded",
        finished=True,
        progress_pct=100,
        current_step="done",
        status_message="Dry-run complete",
    )
    db.append_log(job_id, "Dry-run finished successfully")


def _real_pipeline(job_id: str, params: dict[str, Any]) -> None:
    import fastf1
    from google.cloud import bigquery

    import f1_telemetry_import as pipe

    years = sorted(set(int(y) for y in params["years"]))
    race = str(params["race"])
    session_types = list(params.get("sessions") or ["R"])
    skip_existing = not bool(params.get("noSkip"))
    skip_quality = bool(params.get("skipQuality"))
    skip_unified = bool(params.get("skipUnified"))
    include_kaggle = bool(params.get("includeKaggle"))

    cache_dir = os.environ.get(
        "FASTF1_CACHE_DIR", os.path.expanduser("~/.cache/fastf1")
    )
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)

    client = bigquery.Client(project=pipe.PROJECT)
    db.append_log(job_id, f"BigQuery project={pipe.PROJECT} dataset={pipe.DATASET}")
    db.append_log(job_id, f"FastF1 cache={cache_dir}")

    state: dict[str, Any] = {
        "existing": {},
        "loaded": {},
        "telemetry_df": None,
        "laps_df": None,
    }

    def load():
        if skip_existing:
            state["existing"] = pipe.check_existing(
                client, years, race, session_types
            )
        loaded = pipe.load_sessions(
            years, race, session_types, skip_existing, state["existing"]
        )
        if not loaded:
            raise RuntimeError("Nothing to import (no sessions loaded)")
        state["loaded"] = loaded

    def resample():
        telemetry_df, laps_df = pipe.extract_telemetry(state["loaded"])
        state["telemetry_df"] = telemetry_df
        state["laps_df"] = laps_df
        db.append_log(
            job_id,
            f"Extracted {len(telemetry_df):,} telemetry rows, {len(laps_df):,} laps",
        )

    def upload_sessions():
        pipe.upload_sessions_and_laps(
            client, state["loaded"], state["laps_df"], race
        )

    def upload_telemetry():
        pipe.upload_telemetry(client, state["telemetry_df"], state["loaded"])

    def verify():
        pipe.verify_upload(client, years, race, session_types)

    def quality():
        pipe.run_quality_checks(client, state["loaded"], race)

    def unified():
        pipe.update_laps_unified(client, state["loaded"])

    def kaggle():
        import kaggle_upload as kag

        # Reuse kaggle_upload.main() logic
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        bq = bigquery.Client(project=kag.PROJECT)
        existing_df = kag.download_current_kaggle_data(api)
        bq_laps = kag.fetch_bq_laps(bq)
        if bq_laps.empty:
            db.append_log(job_id, "No laps in BigQuery for Kaggle upload")
            return
        new_laps = kag.find_new_laps(bq_laps, existing_df)
        if new_laps.empty:
            db.append_log(job_id, "Kaggle already up to date — nothing new")
            return
        telemetry_df = kag.fetch_telemetry_for_laps(bq, new_laps)
        new_rows = kag.build_kaggle_rows(new_laps, telemetry_df)
        if existing_df.empty:
            combined = new_rows
        else:
            existing_trimmed = existing_df[
                new_rows.columns.intersection(existing_df.columns)
            ]
            import pandas as pd

            combined = pd.concat([existing_trimmed, new_rows], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=[
                "season",
                "event_name",
                "session_type",
                "driver_number",
                "lap_number",
            ]
        )
        kag.upload_to_kaggle(api, combined)

    plan: list[tuple[str, str, Callable[[], None]]] = [
        ("load_fastf1", "Load FastF1 sessions", load),
        ("resample_telemetry", "Resample telemetry", resample),
        ("upload_sessions_laps", "Upload sessions & laps", upload_sessions),
        ("upload_telemetry", "Upload telemetry", upload_telemetry),
        ("verify", "Verify upload", verify),
    ]
    if not skip_quality:
        plan.append(("quality_checks", "Quality checks", quality))
    if not skip_unified:
        plan.append(("laps_unified", "Update laps_unified", unified))
    if include_kaggle:
        plan.append(("kaggle_upload", "Kaggle upload", kaggle))
    plan.append(("done", "Finalize", lambda: None))

    for step_key, label, fn in plan:
        ok = _run_step(job_id, params, step_key, label, fn)
        if not ok:
            _mark_cancelled(job_id, params, step_key)
            return

    db.update_job(
        job_id,
        status="succeeded",
        finished=True,
        progress_pct=100,
        current_step="done",
        status_message="Import complete",
    )
    db.append_log(job_id, "✅ Pipeline succeeded")


def run(job_id: str) -> int:
    job = db.get_job(job_id)
    if not job:
        print(f"Job not found: {job_id}", file=sys.stderr)
        return 1

    params = _params(job)
    db.update_job(
        job_id,
        status="running",
        started=True,
        status_message="Worker started",
        current_step="load_fastf1",
    )
    db.append_log(
        job_id,
        f"Worker started for {params.get('race')} ({params.get('years')})",
    )

    try:
        if os.environ.get("WORKER_DRY_RUN", "").lower() in {"1", "true", "yes"}:
            db.append_log(job_id, "WORKER_DRY_RUN enabled — skipping FastF1/BQ")
            _dry_run(job_id, params)
        else:
            _real_pipeline(job_id, params)
        return 0
    except Exception as exc:
        db.update_job(
            job_id,
            status="failed",
            finished=True,
            error=str(exc),
            status_message="Pipeline failed",
        )
        db.append_log(job_id, f"Pipeline failed: {exc}", level="error")
        print(traceback.format_exc(), file=sys.stderr)
        return 1
