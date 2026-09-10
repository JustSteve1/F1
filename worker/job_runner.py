"""
Orchestrates the F1 telemetry import pipeline for a single JOB_ID,
emitting step progress / logs into Postgres.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

# Ensure pipeline package is importable
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

import db  # noqa: E402
from ingest_source import assert_fastf1_ingest  # noqa: E402
from job_control import desired_status_on_stop  # noqa: E402

STEP_ORDER = [
    "load_fastf1",
    "resample_telemetry",
    "upload_kaggle_export",
    "upload_sessions_laps",
    "upload_telemetry",
    "verify",
    "quality_checks",
    "laps_unified",
    "kaggle_upload",
    "done",
]

# Per-step wall-clock caps (seconds). Cloud Run --task-timeout is 14400 (4h).
# Budget is per active path (Kaggle-only vs warehouse), not the sum of every key.
STEP_TIMEOUTS_SEC: dict[str, int] = {
    "load_fastf1": 20 * 60,
    "resample_telemetry": 90 * 60,
    "upload_kaggle_export": 15 * 60,
    "upload_sessions_laps": 15 * 60,
    "upload_telemetry": 45 * 60,
    "verify": 10 * 60,
    "quality_checks": 20 * 60,
    "laps_unified": 15 * 60,
    "kaggle_upload": 40 * 60,
    "done": 5 * 60,
}
HEARTBEAT_SEC = 30


def _install_stop_handlers(job_id: str) -> None:
    def handler(signum: int, _frame: Any) -> None:
        job = db.get_job(job_id)
        if job:
            nxt = desired_status_on_stop(str(job.get("status") or ""))
            if nxt == "cancelled":
                _mark_cancelled(
                    job_id,
                    _params(job),
                    str(job.get("current_step") or "load_fastf1"),
                )
            elif nxt == "failed":
                db.update_job(
                    job_id,
                    status="failed",
                    finished=True,
                    error=f"Worker received signal {signum} (Cloud Run cancelled or SIGTERM)",
                    status_message="Worker stopped",
                )
                db.append_log(
                    job_id,
                    f"Worker received signal {signum}",
                    level="error",
                )
        raise SystemExit(128 + int(signum))

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def _params(job: dict[str, Any]) -> dict[str, Any]:
    p = job.get("params") or {}
    if isinstance(p, str):
        import json

        p = json.loads(p)
    return p


def _active_steps(params: dict[str, Any]) -> list[str]:
    steps = list(STEP_ORDER)
    include_kaggle = bool(params.get("includeKaggle"))
    if include_kaggle:
        steps = [
            s
            for s in steps
            if s
            not in (
                "upload_sessions_laps",
                "upload_telemetry",
                "verify",
                "laps_unified",
            )
        ]
    else:
        steps = [
            s
            for s in steps
            if s not in ("upload_kaggle_export", "kaggle_upload")
        ]
    if params.get("skipQuality"):
        steps = [s for s in steps if s != "quality_checks"]
    if params.get("skipUnified"):
        steps = [s for s in steps if s != "laps_unified"]
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
    if db.should_stop(job_id):
        return False

    db.begin_step(job_id, step_key, label)
    db.update_job(
        job_id,
        current_step=step_key,
        progress_pct=_progress(step_key, params),
        status_message=f"Running: {label}",
    )
    db.append_log(job_id, f"▶ {label}")
    db.heartbeat(job_id)

    timeout = STEP_TIMEOUTS_SEC.get(step_key, 30 * 60)
    done = threading.Event()
    box: list[BaseException] = []

    def runner() -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 — propagate to waiter
            box.append(exc)
        finally:
            done.set()

    thread = threading.Thread(target=runner, name=f"step-{step_key}", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout

    try:
        while not done.wait(timeout=HEARTBEAT_SEC):
            db.heartbeat(job_id)
            if db.should_stop(job_id):
                db.finish_step(job_id, step_key, "cancelled", "Cancelled")
                return False
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"{label} exceeded {timeout // 60} min step cap"
                )
        if box:
            raise box[0]
        if db.should_stop(job_id):
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
            job = db.get_job(job_id)
            if job and str(job.get("status")) == "cancelling":
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
            if include_kaggle:
                import kaggle_export as kexp

                state["existing"] = kexp.check_existing_kaggle_export(
                    client, years, race, session_types
                )
            else:
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
        telemetry_df, laps_df = pipe.extract_telemetry(
            state["loaded"], log=_cache_log
        )
        state["telemetry_df"] = telemetry_df
        state["laps_df"] = laps_df
        db.append_log(
            job_id,
            f"Extracted {len(telemetry_df):,} telemetry rows, {len(laps_df):,} laps",
        )
        pipe.write_resample_checkpoint(
            job_id, telemetry_df, laps_df, log=_cache_log
        )

    def upload_kaggle_export():
        if state.get("skip_all_existing"):
            db.append_log(job_id, "Skip kaggle export table — already present")
            return
        import kaggle_export as kexp

        telemetry_df = state.get("telemetry_df")
        if telemetry_df is None:
            cached = pipe.load_resample_checkpoint(job_id, log=_cache_log)
            if cached is None:
                raise RuntimeError(
                    "No telemetry dataframe and no resample checkpoint in GCS"
                )
            telemetry_df, state["laps_df"] = cached
            state["telemetry_df"] = telemetry_df
        kexp.upload_kaggle_export(
            client,
            state["loaded"],
            telemetry_df,
            years=years,
            race=race,
            session_types=session_types,
            log=_cache_log,
            job_id=job_id,
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
        if include_kaggle:
            import kaggle_export as kexp

            kexp.run_kaggle_export_quality_checks(
                client, years, race, session_types, log=_cache_log
            )
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
        export_df = kag.fetch_bq_laps(bq)
        if export_df.empty:
            db.append_log(job_id, "No rows in for_kaggle_export for Kaggle upload")
            return
        combined = kag.merge_kaggle_csv(existing_df, export_df)
        db.append_log(
            job_id,
            f"Kaggle merge: {len(combined):,} rows "
            f"({len(export_df):,} from for_kaggle_export)",
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
    ]
    if include_kaggle:
        plan.append(
            ("upload_kaggle_export", "Upload Kaggle export table", upload_kaggle_export)
        )
    else:
        plan.extend(
            [
                ("upload_sessions_laps", "Upload sessions & laps", upload_sessions),
                ("upload_telemetry", "Upload telemetry", upload_telemetry),
                ("verify", "Verify upload", verify),
            ]
        )
    if not skip_quality:
        plan.append(("quality_checks", "Quality checks", quality))
    if not skip_unified and not include_kaggle:
        plan.append(("laps_unified", "Update laps_unified", unified))
    if include_kaggle:
        plan.append(("kaggle_upload", "Kaggle upload", kaggle))
    plan.append(("done", "Finalize", finalize))

    pipeline_ok = True
    for step_key, label, fn in plan:
        ok = _run_step(job_id, params, step_key, label, fn)
        if not ok:
            pipeline_ok = False
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
        job = db.get_job(job_id)
        if job and str(job.get("status")) == "cancelling":
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
    _install_stop_handlers(job_id)
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
        source = assert_fastf1_ingest()
        db.append_log(job_id, f"INGEST_SOURCE={source}")
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
