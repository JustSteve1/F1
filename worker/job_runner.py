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
    import fastf1_cache_sync

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

    def _cache_log(msg: str) -> None:
        print(msg)
        db.append_log(job_id, msg)

    # Pull seeded/previous FastF1 cache before any livetiming downloads
    try:
        fastf1_cache_sync.pull_cache(cache_dir, log=_cache_log)
    except Exception as pull_err:
        db.append_log(
            job_id,
            f"FastF1 GCS cache pull failed (continuing cold): {pull_err}",
            level="warn",
        )

    fastf1.Cache.enable_cache(cache_dir)

    gcs_uri = os.environ.get("FASTF1_CACHE_GCS_URI", "").strip()

    # Fail fast when GCS cache was expected but race has no seeded folders
    if gcs_uri:
        for year in years:
            inv = pipe._cache_session_inventory(cache_dir, year, race)
            if not inv.get("event_dirs"):
                raise RuntimeError(
                    f"No FastF1 cache found for {year} {race} after GCS pull. "
                    "Seed FastF1 cache first (Colab notebook or seed_fastf1_cache.py)."
                )

    client = bigquery.Client(project=pipe.PROJECT)
    db.append_log(job_id, f"BigQuery project={pipe.PROJECT} dataset={pipe.DATASET}")
    db.append_log(job_id, f"FastF1 cache={cache_dir}")
    if gcs_uri:
        db.append_log(job_id, f"FastF1 GCS cache URI={gcs_uri}")

    state: dict[str, Any] = {
        "existing": {},
        "loaded": {},
        "telemetry_df": None,
        "laps_df": None,
        "skip_all_existing": False,
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
            requested = {(y, s) for y in years for s in session_types}
            already = set(state["existing"].keys()) & requested
            if skip_existing and already and already == requested:
                db.append_log(
                    job_id,
                    "All requested sessions already in BigQuery — skipping FastF1 import",
                )
                state["loaded"] = {}
                state["skip_all_existing"] = True
                return
            raise RuntimeError(
                "Nothing to import (no sessions loaded — all skipped or FastF1 failed)"
            )
        state["loaded"] = loaded
        state["skip_all_existing"] = False

    def resample():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip resample — no new sessions")
            return
        cached = pipe.load_resample_checkpoint(job_id, log=_cache_log)
        if cached is not None:
            state["telemetry_df"], state["laps_df"] = cached
            return
        telemetry_df, laps_df = pipe.extract_telemetry(state["loaded"])
        state["telemetry_df"] = telemetry_df
        state["laps_df"] = laps_df
        db.append_log(
            job_id,
            f"Extracted {len(telemetry_df):,} telemetry rows, {len(laps_df):,} laps",
        )
        pipe.write_resample_checkpoint(
            job_id, telemetry_df, laps_df, log=_cache_log
        )

    def upload_sessions():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip sessions/laps upload — already present")
            return
        pipe.upload_sessions_and_laps(
            client, state["loaded"], state["laps_df"], race,
            log=_cache_log,
            job_id=job_id,
        )

    def upload_telemetry():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip telemetry upload — already present")
            return
        telemetry_df = state.get("telemetry_df")
        if telemetry_df is None or len(telemetry_df) == 0:
            cached = pipe.load_resample_checkpoint(job_id, log=_cache_log)
            if cached is None:
                raise RuntimeError(
                    "No telemetry dataframe and no resample checkpoint in GCS"
                )
            telemetry_df, state["laps_df"] = cached
            state["telemetry_df"] = telemetry_df
        pipe.upload_telemetry(
            client,
            telemetry_df,
            state["loaded"],
            log=_cache_log,
            job_id=job_id,
        )

    def verify():
        pipe.verify_upload(client, years, race, session_types)

    def quality():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip quality checks — no new sessions")
            return
        pipe.run_quality_checks(client, state["loaded"], race)

    def unified():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip laps_unified — no new sessions")
            return
        pipe.update_laps_unified(client, state["loaded"])

    def kaggle():
        import kaggle_upload as kag
        from kaggle.api.kaggle_api_extended import KaggleApi
        kag.ensure_kaggle_auth()

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
        kag.upload_to_kaggle(combined)

    def finalize():
        try:
            pipe.delete_resample_checkpoint(job_id, log=_cache_log)
        except Exception as ck_err:
            db.append_log(
                job_id,
                f"Checkpoint cleanup failed (non-fatal): {ck_err}",
                level="warn",
            )

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
    plan.append(("done", "Finalize", finalize))

    pipeline_ok = True
    for step_key, label, fn in plan:
        ok = _run_step(job_id, params, step_key, label, fn)
        if not ok:
            pipeline_ok = False
            _mark_cancelled(job_id, params, step_key)
            break

    # Persist any cache files obtained this run (success or partial)
    try:
        fastf1_cache_sync.push_cache(cache_dir, log=_cache_log)
    except Exception as push_err:
        db.append_log(
            job_id,
            f"FastF1 GCS cache push failed: {push_err}",
            level="warn",
        )

    if not pipeline_ok:
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

    cache_dir = os.environ.get(
        "FASTF1_CACHE_DIR", os.path.expanduser("~/.cache/fastf1")
    )

    try:
        if os.environ.get("WORKER_DRY_RUN", "").lower() in {"1", "true", "yes"}:
            db.append_log(job_id, "WORKER_DRY_RUN enabled — skipping FastF1/BQ")
            _dry_run(job_id, params)
        else:
            _real_pipeline(job_id, params)
        return 0
    except Exception as exc:
        # Best-effort: keep any partial FastF1 downloads for the next run
        try:
            import fastf1_cache_sync

            fastf1_cache_sync.push_cache(
                cache_dir,
                log=lambda m: db.append_log(job_id, m, level="warn"),
            )
        except Exception:
            pass
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
