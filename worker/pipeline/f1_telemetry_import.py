"""
F1 Telemetry Import Pipeline — CLI version of Step_1_Telemetry_Import_v2_0_(FastF1)

Usage:
    python f1_telemetry_import.py --year 2025 --race "Australian Grand Prix" --session R
    python f1_telemetry_import.py --year 2024 2025 --race "Monaco Grand Prix" --session Q R
    python f1_telemetry_import.py --year 2025 --race "Australian Grand Prix" --session R --no-skip

Auth:
    Uses Google Application Default Credentials (ADC).
    Run: gcloud auth application-default login
    Or set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

Requirements:
    pip install fastf1 google-cloud-bigquery pandas numpy matplotlib seaborn db-dtypes pyarrow
"""

import argparse
import hashlib
import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import fastf1
import numpy as np
import pandas as pd
from google.cloud import bigquery

warnings.filterwarnings("ignore")

# ── Config (override via environment variables) ───────────────────────────────

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
TELEMETRY_INTERVAL = float(os.environ.get("TELEMETRY_INTERVAL", "0.1"))  # 10 Hz

MIN_LAP_TIME = 60.0
MAX_LAP_TIME = 300.0
MIN_LAPS_PER_SESSION = 5
MAX_TELEMETRY_GAP = 5.0

DEFAULT_CACHE_DIR = os.environ.get("FASTF1_CACHE_DIR", os.path.expanduser("~/.cache/fastf1"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_session_key(year: int, race: str, session_type: str) -> int:
    key_str = f"{year}-{race}-{session_type}"
    return int(hashlib.md5(key_str.encode()).hexdigest()[:8], 16)


def timedelta_to_seconds(td):
    if pd.isna(td) or td is None:
        return None
    return td.total_seconds()


def to_timestamp(dt):
    if pd.isna(dt) or dt is None:
        return None
    return dt.isoformat()


def safe_int(val):
    if pd.isna(val) or val is None:
        return None
    return int(val)


def safe_float(val):
    if pd.isna(val) or val is None:
        return None
    return float(val)


def safe_bool(val):
    if pd.isna(val) or val is None:
        return None
    return bool(val)


def safe_str(val):
    if pd.isna(val) or val is None:
        return None
    return str(val)


def upload_in_batches(client, table_ref, rows, batch_size=1000, label="rows"):
    """Streaming insert for small tables (sessions). Do not use for telemetry."""
    total = len(rows)
    uploaded = 0
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        errors = client.insert_rows_json(table_ref, batch)
        if errors:
            print(f"  ⚠  Batch {i//batch_size + 1} errors: {errors[:2]}")
        uploaded += len(batch)
        if total > batch_size and uploaded % 10_000 == 0:
            print(f"  {uploaded:,} / {total:,} {label} uploaded…")
    return uploaded


def _staging_parquet_uri(job_id: str | None, filename: str) -> str:
    cache_uri = os.environ.get("FASTF1_CACHE_GCS_URI", "").strip()
    bucket = "f1-data-library-fastf1-cache"
    if cache_uri.startswith("gs://"):
        bucket = urlparse(cache_uri).netloc or bucket
    jid = job_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"gs://{bucket}/staging/{jid}/{filename}"


def _gcs_blob(uri: str):
    from google.cloud import storage

    parsed = urlparse(uri)
    client = storage.Client()
    return client.bucket(parsed.netloc).blob(parsed.path.lstrip("/")), client


def write_resample_checkpoint(job_id: str, telemetry_df, laps_df, *, log=print) -> dict:
    """Persist resampled frames so upload can resume after a Cloud Run kill."""
    tel_uri = _staging_parquet_uri(job_id, "telemetry.parquet")
    laps_uri = _staging_parquet_uri(job_id, "laps.parquet")
    tmp = Path("/tmp") / f"ckpt-{job_id}"
    tmp.mkdir(parents=True, exist_ok=True)
    tel_path = tmp / "telemetry.parquet"
    laps_path = tmp / "laps.parquet"
    telemetry_df.to_parquet(tel_path, index=False)
    (laps_df if laps_df is not None else pd.DataFrame()).to_parquet(
        laps_path, index=False
    )
    tel_blob, _ = _gcs_blob(tel_uri)
    laps_blob, _ = _gcs_blob(laps_uri)
    tel_blob.upload_from_filename(str(tel_path))
    laps_blob.upload_from_filename(str(laps_path))
    log(
        f"Wrote resample checkpoint {tel_uri} "
        f"({len(telemetry_df):,} telemetry rows, {len(laps_df) if laps_df is not None else 0:,} laps)"
    )
    return {
        "telemetry_uri": tel_uri,
        "laps_uri": laps_uri,
        "telemetry_rows": int(len(telemetry_df)),
        "laps_rows": int(len(laps_df) if laps_df is not None else 0),
    }


def load_resample_checkpoint(job_id: str, *, log=print):
    """Return (telemetry_df, laps_df) if a checkpoint exists, else None."""
    tel_uri = _staging_parquet_uri(job_id, "telemetry.parquet")
    laps_uri = _staging_parquet_uri(job_id, "laps.parquet")
    tel_blob, _ = _gcs_blob(tel_uri)
    if not tel_blob.exists():
        return None
    tmp = Path("/tmp") / f"ckpt-load-{job_id}"
    tmp.mkdir(parents=True, exist_ok=True)
    tel_path = tmp / "telemetry.parquet"
    laps_path = tmp / "laps.parquet"
    tel_blob.download_to_filename(str(tel_path))
    telemetry_df = pd.read_parquet(tel_path)
    laps_df = pd.DataFrame()
    laps_blob, _ = _gcs_blob(laps_uri)
    if laps_blob.exists():
        laps_blob.download_to_filename(str(laps_path))
        laps_df = pd.read_parquet(laps_path)
    log(
        f"Using checkpoint from {tel_uri} "
        f"({len(telemetry_df):,} telemetry rows, {len(laps_df):,} laps)"
    )
    return telemetry_df, laps_df


def delete_resample_checkpoint(job_id: str, *, log=print) -> int:
    """Remove staging/{job_id}/ after a successful pipeline."""
    marker = _staging_parquet_uri(job_id, "_")
    parsed = urlparse(marker)
    prefix = parsed.path.lstrip("/").rsplit("/", 1)[0] + "/"
    from google.cloud import storage

    client = storage.Client()
    deleted = 0
    for blob in client.list_blobs(parsed.netloc, prefix=prefix):
        blob.delete()
        deleted += 1
    log(f"Deleted {deleted} checkpoint object(s) under gs://{parsed.netloc}/{prefix}")
    return deleted


def _coerce_df_for_table(client, table_ref: str, df: pd.DataFrame) -> pd.DataFrame:
    """Align pandas dtypes to an existing BigQuery table schema."""
    table = client.get_table(table_ref)
    out = pd.DataFrame(index=df.index)
    for field in table.schema:
        if field.name not in df.columns:
            continue
        col = df[field.name]
        ftype = (field.field_type or "").upper()
        if ftype in ("INTEGER", "INT64"):
            out[field.name] = pd.to_numeric(col, errors="coerce").astype("Int64")
        elif ftype in ("FLOAT", "FLOAT64", "NUMERIC", "BIGNUMERIC"):
            out[field.name] = pd.to_numeric(col, errors="coerce")
        elif ftype in ("BOOLEAN", "BOOL"):
            out[field.name] = col.map(
                lambda v: None
                if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v)
                else bool(v)
            ).astype("boolean")
        elif ftype in ("TIMESTAMP", "DATETIME"):
            out[field.name] = pd.to_datetime(col, utc=True, errors="coerce")
        elif ftype == "DATE":
            ts = pd.to_datetime(col, utc=True, errors="coerce")
            out[field.name] = ts.dt.date
        else:
            out[field.name] = col.map(
                lambda v: None
                if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v)
                else str(v)
            )
    return out


def load_dataframe(
    client,
    table_ref: str,
    df: pd.DataFrame,
    *,
    log=print,
    job_id: str | None = None,
    label: str = "rows",
) -> dict:
    """Bulk-append a DataFrame via a BigQuery load job (not streaming insert).

    Tries load_table_from_dataframe first. On schema/type failure, writes Parquet
    to gs://<cache-bucket>/staging/{job_id}/ and loads from URI.
    """
    if df is None or len(df) == 0:
        log(f"No {label} to load")
        return {"rows": 0, "bq_job_id": None, "method": "skip"}

    coerced = _coerce_df_for_table(client, table_ref, df)
    table = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=table.schema,
    )
    try:
        load_job = client.load_table_from_dataframe(
            coerced, table_ref, job_config=job_config
        )
        load_job.result()
        log(
            f"BigQuery load job {load_job.job_id}: "
            f"{len(coerced):,} {label} → {table_ref} (dataframe)"
        )
        return {
            "rows": len(coerced),
            "bq_job_id": load_job.job_id,
            "method": "dataframe",
        }
    except Exception as exc:
        log(
            f"load_table_from_dataframe failed ({exc}); "
            "falling back to Parquet GCS load"
        )

    uri = _staging_parquet_uri(job_id, f"{label.replace(' ', '_')}.parquet")
    parsed = urlparse(uri)
    local_path = Path("/tmp") / parsed.path.lstrip("/").replace("/", "_")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    coerced.to_parquet(local_path, index=False)

    from google.cloud import storage

    storage.Client().bucket(parsed.netloc).blob(
        parsed.path.lstrip("/")
    ).upload_from_filename(str(local_path))
    parquet_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.PARQUET,
        schema=table.schema,
    )
    load_job = client.load_table_from_uri(uri, table_ref, job_config=parquet_config)
    load_job.result()
    log(
        f"BigQuery load job {load_job.job_id}: "
        f"{len(coerced):,} {label} → {table_ref} (parquet {uri})"
    )
    return {
        "rows": len(coerced),
        "bq_job_id": load_job.job_id,
        "method": "parquet",
        "uri": uri,
    }


def session_keys_for_loaded(loaded_sessions) -> list[int]:
    keys: list[int] = []
    for (year, stype), session in loaded_sessions.items():
        keys.append(
            generate_session_key(year, session.event["EventName"], stype)
        )
    return keys


def delete_session_rows(client, session_keys, tables, *, log=print) -> None:
    """Remove existing warehouse rows for these session_keys (replace, not append)."""
    keys = [int(k) for k in session_keys if k is not None]
    if not keys:
        return
    key_list = ", ".join(str(k) for k in keys)
    for table in tables:
        q = (
            f"DELETE FROM `{PROJECT}.{DATASET}.{table}` "
            f"WHERE session_key IN ({key_list})"
        )
        job = client.query(q)
        job.result()
        affected = job.num_dml_affected_rows
        log(
            f"Deleted {affected if affected is not None else '?'} "
            f"{table} row(s) for session_key IN ({key_list}) "
            f"(job {job.job_id})"
        )


# ── Step 1: Check existing data ───────────────────────────────────────────────

def check_existing(client, years, race, session_types):
    year_list = ", ".join(map(str, years))
    session_list = ", ".join(f"'{s}'" for s in session_types)
    query = f"""
        SELECT DISTINCT season, session_type
        FROM `{PROJECT}.{DATASET}.telemetry`
        WHERE season IN ({year_list})
          AND event_name = '{race}'
          AND session_type IN ({session_list})
    """
    try:
        df = client.query(query).to_dataframe()
        return {(int(r["season"]), r["session_type"]): True for _, r in df.iterrows()}
    except Exception:
        return {}


# ── Step 2: Load FastF1 sessions ──────────────────────────────────────────────


def _cache_session_inventory(cache_dir: str, year: int, race: str) -> dict:
    """List cached FastF1 session folder names for year/race (for error context)."""
    from pathlib import Path

    root = Path(cache_dir) / str(year)
    if not root.exists():
        return {"year_dir_exists": False, "event_dirs": [], "session_dirs": []}
    race_token = race.replace(" ", "_")
    event_dirs = sorted(
        p.name for p in root.iterdir() if p.is_dir() and race_token in p.name
    )
    session_dirs = []
    for ed in event_dirs:
        for child in sorted((root / ed).iterdir()):
            if child.is_dir():
                files = [f.name for f in child.iterdir() if f.is_file()]
                session_dirs.append(
                    {
                        "event": ed,
                        "session": child.name,
                        "has_timing": "timing_app_data.ff1pkl" in files,
                        "file_count": len(files),
                    }
                )
    return {
        "year_dir_exists": True,
        "event_dirs": event_dirs,
        "session_dirs": session_dirs,
    }


def _laps_accessible(session):
    """Return (ok, n_or_none, error_str_or_none)."""
    try:
        n = len(session.laps)
        return True, n, None
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"


class _WarningCapture(logging.Handler):
    """Collect FastF1 warning messages during session.load()."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        if msg:
            self.messages.append(msg)


def _load_session_with_retries(year, race, stype, attempts=5):
    """Load a FastF1 session with retries and telemetry fallback."""
    import time

    last_err = None
    for attempt in range(1, attempts + 1):
        warn_cap = _WarningCapture()
        f1_logger = logging.getLogger("fastf1")
        f1_logger.addHandler(warn_cap)
        try:
            session = fastf1.get_session(year, race, stype)
            load_raised = None
            try:
                session.load(telemetry=True, laps=True, weather=False)
            except Exception as tel_err:
                load_raised = f"{type(tel_err).__name__}: {tel_err}"
            ok, n, laps_err = _laps_accessible(session)
            if load_raised or not ok:
                # Soft-fail: FastF1 often returns from load() even when timing
                # data failed (common on Cloud Run). Fall back to laps-only.
                session = fastf1.get_session(year, race, stype)
                fb_raised = None
                try:
                    session.load(telemetry=False, laps=True, weather=False)
                except Exception as fb_err:
                    fb_raised = f"{type(fb_err).__name__}: {fb_err}"
                ok2, n2, laps_err2 = _laps_accessible(session)
                if not ok2:
                    warn_txt = "; ".join(warn_cap.messages[-6:]) or "none"
                    raise RuntimeError(
                        "FastF1 timing data missing after load "
                        "(Cloud Run often needs seeded GCS cache). "
                        f"true_load={load_raised or laps_err}; "
                        f"false_load={fb_raised or laps_err2}; "
                        f"warnings={warn_txt}"
                    )
                if n2 == 0:
                    raise RuntimeError("no laps found after laps-only load")
                probe = session.laps.iloc[0]
                try:
                    telem = probe.get_telemetry()
                    telem_n = 0 if telem is None else len(telem)
                except Exception as probe_err:
                    raise RuntimeError(
                        "telemetry unavailable on this host "
                        f"(laps loaded but get_telemetry failed): {probe_err}"
                    ) from probe_err
                if telem_n == 0:
                    raise RuntimeError(
                        "telemetry unavailable on this host "
                        "(laps loaded but car data empty)"
                    )
            else:
                if n == 0:
                    raise RuntimeError("no laps found")
            return session
        except Exception as e:
            last_err = e
            msg = str(e)
            print(f"  ❌  {year} {stype}: attempt {attempt}/{attempts}: {msg[:200]}")
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 30))
        finally:
            f1_logger.removeHandler(warn_cap)
    assert last_err is not None
    raise last_err


def load_sessions(years, race, session_types, skip_existing, existing):
    loaded = {}
    errors = []
    cache_dir = os.environ.get("FASTF1_CACHE_DIR", "/tmp/fastf1-cache")
    for year in years:
        inv = _cache_session_inventory(cache_dir, year, race)
        for stype in session_types:
            key = (year, stype)
            if skip_existing and key in existing:
                print(f"  ⏭  Skipping {year} {stype} — already in BigQuery")
                continue
            try:
                session = _load_session_with_retries(year, race, stype)
                loaded[key] = session
                print(
                    f"  ✅  {year} {stype}: {len(session.drivers)} drivers, "
                    f"{len(session.laps)} laps"
                )
            except Exception as e:
                err = f"{year} {stype}: {e}"
                cached_names = [
                    s["session"] for s in inv.get("session_dirs", [])
                ]
                if cached_names:
                    err += f" | cached_sessions={cached_names}"
                else:
                    err += " | cached_sessions=[]"
                errors.append(err)
                print(f"  ❌  {err[:240]}")
    if not loaded and errors:
        # Surface root cause instead of opaque "no sessions loaded"
        raise RuntimeError(
            "Nothing to import — FastF1 load failed: " + " | ".join(errors)[:800]
        )
    return loaded


# ── Step 3: Resample telemetry ────────────────────────────────────────────────

_TELEM_LOAD_STATS = {
    "get_telemetry_ok": 0,
    "car_data_fallback_ok": 0,
    "failed": 0,
    "failed_examples": [],
}


def _load_lap_telemetry_frame(lap):
    """
    Load per-lap telemetry robustly.

    FastF1 get_telemetry() merges car_data + pos_data on Date. For Monaco 2026 R
    (and similar), pos_data is empty for most laps while car_data is present;
    get_telemetry() then raises KeyError on Date. Fall back to car_data (+ optional
    pos merge) so speed/throttle/etc. are still captured; XYZ may be null.
    """
    # Preferred: full telemetry with XYZ when position stream exists
    try:
        telem = lap.get_telemetry()
        if telem is not None and len(telem) > 0:
            _TELEM_LOAD_STATS["get_telemetry_ok"] += 1
            return telem, "get_telemetry"
    except Exception as e:
        telem_err = f"{type(e).__name__}: {e}"
    else:
        telem_err = "empty_get_telemetry"

    # Fallback: car channels always; merge pos when available for XYZ
    try:
        car = lap.get_car_data()
        if car is None or len(car) == 0:
            raise RuntimeError("empty_car_data")
        try:
            pos = lap.get_pos_data()
            if pos is not None and len(pos) > 0 and hasattr(car, "merge_channels"):
                car = car.merge_channels(pos)
        except Exception:
            pass
        if "Distance" not in getattr(car, "columns", []):
            car = car.add_distance()
        _TELEM_LOAD_STATS["car_data_fallback_ok"] += 1
        return car, "car_data_fallback"
    except Exception as e:
        _TELEM_LOAD_STATS["failed"] += 1
        if len(_TELEM_LOAD_STATS["failed_examples"]) < 10:
            _TELEM_LOAD_STATS["failed_examples"].append({
                "driver": str(lap.get("DriverNumber")),
                "lap": safe_int(lap.get("LapNumber")),
                "get_telemetry_err": telem_err,
                "fallback_err": f"{type(e).__name__}: {e}",
            })
        return None, "failed"


def resample_lap_telemetry(lap, interval_sec=TELEMETRY_INTERVAL):
    try:
        telemetry, _source = _load_lap_telemetry_frame(lap)
        if telemetry is None or len(telemetry) == 0:
            return []

        telemetry = telemetry.copy()
        telemetry["Time_sec"] = telemetry["Time"].dt.total_seconds()
        lap_duration = telemetry["Time_sec"].max()
        num_intervals = int(np.ceil(lap_duration / interval_sec))
        target_times = np.arange(0, num_intervals) * interval_sec

        resampled = []
        for t in target_times:
            if t > lap_duration:
                break
            idx = (telemetry["Time_sec"] - t).abs().idxmin()
            row = telemetry.loc[idx]

            prev_rows = telemetry[telemetry["Time_sec"] < t]
            if len(prev_rows) > 0 and row["Speed"] is not None:
                decel = (row["Speed"] - prev_rows["Speed"].iloc[-1]) / interval_sec
            else:
                decel = 0.0

            distance_m = (float(row["Speed"]) / 3.6) * interval_sec if pd.notna(row["Speed"]) else 0.0

            resampled.append({
                "driver_number": str(lap["DriverNumber"]),
                "lap_number": int(lap["LapNumber"]),
                "lap_time_sec": round(t, 3),
                "interval_sec": interval_sec,
                "speed": safe_float(row.get("Speed")),
                "throttle": safe_float(row.get("Throttle")),
                "brake": bool(row["Brake"]) if pd.notna(row.get("Brake")) else False,
                "gear": safe_int(row.get("nGear")),
                "rpm": safe_float(row.get("RPM")),
                "drs": safe_int(row.get("DRS")),
                "x": safe_float(row.get("X")) if "X" in telemetry.columns else None,
                "y": safe_float(row.get("Y")) if "Y" in telemetry.columns else None,
                "z": safe_float(row.get("Z")) if "Z" in telemetry.columns else None,
                "deceleration": round(decel, 2),
                "distance_m": round(distance_m, 2),
                "cumulative_distance": safe_float(row.get("Distance")) if "Distance" in telemetry.columns else None,
            })
        return resampled
    except Exception:
        return []


def extract_telemetry(loaded_sessions):
    all_telemetry = []
    all_laps = []
    _TELEM_LOAD_STATS["get_telemetry_ok"] = 0
    _TELEM_LOAD_STATS["car_data_fallback_ok"] = 0
    _TELEM_LOAD_STATS["failed"] = 0
    _TELEM_LOAD_STATS["failed_examples"] = []

    for (year, stype), session in loaded_sessions.items():
        event_name = session.event["EventName"]
        circuit = session.event.get("Location", "")
        print(f"  Extracting {year} {stype} ({len(session.laps)} laps)…")
        laps_with_points = 0

        for _, lap in session.laps.iterrows():
            points = resample_lap_telemetry(lap)
            if points:
                laps_with_points += 1
            for p in points:
                p.update({"season": year, "session_type": stype, "event_name": event_name, "circuit": circuit})
            all_telemetry.extend(points)

            all_laps.append({
                "season": year,
                "session_type": stype,
                "event_name": event_name,
                "circuit": circuit,
                "driver_number": safe_str(lap.get("DriverNumber")),
                "lap_number": safe_int(lap.get("LapNumber")),
                "lap_duration": timedelta_to_seconds(lap.get("LapTime")),
                "compound": safe_str(lap.get("Compound")),
                "tyre_age_laps": safe_int(lap.get("TyreLife")),
                "stint_number": safe_int(lap.get("Stint")),
                "sector_1": timedelta_to_seconds(lap.get("Sector1Time")),
                "sector_2": timedelta_to_seconds(lap.get("Sector2Time")),
                "sector_3": timedelta_to_seconds(lap.get("Sector3Time")),
            })
        print(
            f"     telem coverage: {laps_with_points}/{len(session.laps)} laps "
            f"(get_telemetry={_TELEM_LOAD_STATS['get_telemetry_ok']}, "
            f"car_fallback={_TELEM_LOAD_STATS['car_data_fallback_ok']}, "
            f"failed={_TELEM_LOAD_STATS['failed']})"
        )

    telemetry_df = pd.DataFrame(all_telemetry).drop_duplicates(
        subset=["season", "session_type", "driver_number", "lap_number", "lap_time_sec"]
    )
    laps_df = pd.DataFrame(all_laps)
    print(f"  ✅  {len(telemetry_df):,} telemetry points, {len(laps_df):,} laps extracted")
    return telemetry_df, laps_df


# ── Step 4: Upload sessions + laps ───────────────────────────────────────────

def upload_sessions_and_laps(client, loaded_sessions, laps_df, race, *, log=print, job_id=None):
    now = datetime.now(timezone.utc).isoformat()
    keys = session_keys_for_loaded(loaded_sessions)
    # Replace this session's facts; do not append duplicates on retry.
    delete_session_rows(client, keys, ("laps", "telemetry"), log=log)

    # Sessions — skip if session_key already present
    sessions_rows = []
    for (year, stype), session in loaded_sessions.items():
        sk = generate_session_key(year, session.event["EventName"], stype)
        sessions_rows.append({
            "session_key": sk,
            "meeting_key": sk,
            "season": year,
            "event_name": session.event["EventName"],
            "circuit": session.event.get("Location", race),
            "circuit_short_name": race,
            "location": session.event.get("Location", race),
            "country_name": session.event.get("Country", "Unknown"),
            "session_name": session.name,
            "session_type": stype,
            "date_start": session.date.isoformat() if session.date else None,
            "date_end": None,
            "imported_at": now,
        })

    existing_sk: set[int] = set()
    if keys:
        key_list = ", ".join(str(k) for k in keys)
        try:
            existing_df = client.query(
                f"SELECT session_key FROM `{PROJECT}.{DATASET}.sessions` "
                f"WHERE session_key IN ({key_list})"
            ).to_dataframe()
            existing_sk = {int(v) for v in existing_df["session_key"].tolist()}
        except Exception as exc:
            log(f"Session existence check failed (inserting all): {exc}")

    new_sessions = [r for r in sessions_rows if r["session_key"] not in existing_sk]
    skipped = len(sessions_rows) - len(new_sessions)
    if skipped:
        log(f"Skip {skipped} existing session row(s)")
    if new_sessions:
        errors = client.insert_rows_json(
            f"{PROJECT}.{DATASET}.sessions", new_sessions
        )
        if errors:
            log(f"Session upload errors: {errors[:2]}")
        else:
            log(f"{len(new_sessions)} session(s) uploaded")
    elif not sessions_rows:
        log("No sessions to upload")

    # Laps — full schema; session already wiped
    laps_full = []
    for (year, stype), session in loaded_sessions.items():
        sk = generate_session_key(year, session.event["EventName"], stype)
        for _, lap in session.laps.iterrows():
            laps_full.append({
                "session_key": sk,
                "meeting_key": sk,
                "season": year,
                "event_name": session.event["EventName"],
                "session_type": stype,
                "driver_number": safe_str(lap.get("DriverNumber")),
                "driver_code": safe_str(lap.get("Driver")),
                "team": safe_str(lap.get("Team")),
                "position": safe_int(lap.get("Position")),
                "lap_number": safe_int(lap.get("LapNumber")),
                "lap_duration": timedelta_to_seconds(lap.get("LapTime")),
                "lap_start_time": timedelta_to_seconds(lap.get("Time")),
                "sector_1_time": timedelta_to_seconds(lap.get("Sector1Time")),
                "sector_2_time": timedelta_to_seconds(lap.get("Sector2Time")),
                "sector_3_time": timedelta_to_seconds(lap.get("Sector3Time")),
                "sector_1_session_time": timedelta_to_seconds(lap.get("Sector1SessionTime")),
                "sector_2_session_time": timedelta_to_seconds(lap.get("Sector2SessionTime")),
                "sector_3_session_time": timedelta_to_seconds(lap.get("Sector3SessionTime")),
                "pit_out_time": timedelta_to_seconds(lap.get("PitOutTime")),
                "pit_in_time": timedelta_to_seconds(lap.get("PitInTime")),
                "speed_i1": safe_float(lap.get("SpeedI1")),
                "speed_i2": safe_float(lap.get("SpeedI2")),
                "speed_st": safe_float(lap.get("SpeedST")),
                "compound": safe_str(lap.get("Compound")),
                "tyre_age_laps": safe_int(lap.get("TyreLife")),
                "stint_number": safe_int(lap.get("Stint")),
                "fresh_tyre": safe_bool(lap.get("FreshTyre")),
                "is_accurate": safe_bool(lap.get("IsAccurate")),
                "is_personal_best": safe_bool(lap.get("IsPersonalBest")),
                "deleted": safe_bool(lap.get("Deleted")),
                "deleted_reason": safe_str(lap.get("DeletedReason")),
                "fastf1_generated": safe_bool(lap.get("FastF1Generated")),
                "track_status": safe_str(lap.get("TrackStatus")),
                "lap_start_date": to_timestamp(lap.get("LapStartDate")),
                "imported_at": now,
            })

    if laps_full:
        result = load_dataframe(
            client,
            f"{PROJECT}.{DATASET}.laps",
            pd.DataFrame(laps_full),
            log=log,
            job_id=job_id,
            label="laps",
        )
        log(f"{result['rows']:,} laps uploaded")
        return result
    log("No new laps to upload")
    return {"rows": 0, "bq_job_id": None, "method": "skip"}


# ── Step 5: Upload telemetry ──────────────────────────────────────────────────

def upload_telemetry(client, telemetry_df, loaded_sessions, *, log=print, job_id=None):
    now = datetime.now(timezone.utc).isoformat()
    telemetry_df = telemetry_df.copy()
    telemetry_df["imported_at"] = now
    telemetry_df["date"] = now
    telemetry_df["session_key"] = telemetry_df.apply(
        lambda r: generate_session_key(r["season"], r["event_name"], r["session_type"]), axis=1
    )
    telemetry_df["meeting_key"] = telemetry_df["session_key"]
    keys = sorted({int(k) for k in telemetry_df["session_key"].tolist()})
    delete_session_rows(client, keys, ("telemetry",), log=log)

    cols = [
        "session_key", "meeting_key", "season", "driver_number", "lap_number",
        "session_type", "event_name", "circuit",
        "lap_time_sec", "interval_sec",
        "speed", "throttle", "brake", "gear", "rpm", "drs",
        "x", "y", "z",
        "deceleration", "distance_m", "cumulative_distance",
        "date", "imported_at",
    ]
    upload_df = telemetry_df[[c for c in cols if c in telemetry_df.columns]].copy()
    result = load_dataframe(
        client,
        f"{PROJECT}.{DATASET}.telemetry",
        upload_df,
        log=log,
        job_id=job_id,
        label="telemetry points",
    )
    log(f"{result['rows']:,} telemetry points uploaded")
    return result


# ── Step 6: Verify upload ─────────────────────────────────────────────────────

def verify_upload(client, years, race, session_types):
    year_list = ", ".join(map(str, years))
    session_list = ", ".join(f"'{s}'" for s in session_types)
    query = f"""
        SELECT session_type,
               COUNT(*) AS total_points,
               COUNT(DISTINCT driver_number) AS drivers,
               COUNT(DISTINCT lap_number) AS unique_laps,
               ROUND(AVG(speed), 1) AS avg_speed,
               MAX(speed) AS max_speed
        FROM `{PROJECT}.{DATASET}.telemetry`
        WHERE season IN ({year_list})
          AND event_name = '{race}'
          AND session_type IN ({session_list})
          AND imported_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
        GROUP BY session_type
        ORDER BY session_type
    """
    df = client.query(query).to_dataframe()
    print("\n  Upload summary:")
    print(df[["session_type", "total_points", "drivers", "unique_laps", "avg_speed"]].to_string(index=False))
    return df


# ── Step 7: Data quality checks ───────────────────────────────────────────────

def run_quality_checks(client, loaded_sessions, race):
    all_exceptions = []
    now = datetime.utcnow().isoformat()

    for (year, stype), session in loaded_sessions.items():
        session_key = generate_session_key(year, session.event["EventName"], stype)
        exceptions = []

        def add_exc(category, severity, description, extra=None):
            exc = {
                "exception_id": f"{session_key}-{len(exceptions) + 1}",
                "detected_at": now,
                "severity": severity,
                "category": category,
                "description": description,
                "season": year,
                "event_name": session.event["EventName"],
                "session_type": stype,
                "session_key": session_key,
                "driver_number": None,
                "lap_number": None,
                "suggested_action": None,
            }
            if extra:
                exc.update(extra)
            exceptions.append(exc)

        # Check 1: Missing lap data
        try:
            missing_q = f"""
                SELECT driver_number, lap_number, 'missing_lap_duration' AS issue
                FROM `{PROJECT}.{DATASET}.laps`
                WHERE session_key = {session_key} AND lap_duration IS NULL
                UNION ALL
                SELECT driver_number, lap_number, 'missing_sectors'
                FROM `{PROJECT}.{DATASET}.laps`
                WHERE session_key = {session_key}
                  AND sector_1_time IS NULL AND sector_2_time IS NULL AND sector_3_time IS NULL
            """
            missing_df = client.query(missing_q).to_dataframe()
            for _, row in missing_df.iterrows():
                add_exc("missing_data", "warning", row["issue"],
                        {"driver_number": row["driver_number"], "lap_number": int(row["lap_number"])})
        except Exception as e:
            print(f"  ⚠  Check 1 error: {e}")

        # Check 2: Invalid lap times
        try:
            invalid_q = f"""
                SELECT driver_number, lap_number, lap_duration,
                       CASE
                         WHEN lap_duration < {MIN_LAP_TIME} THEN 'too_fast'
                         WHEN lap_duration > {MAX_LAP_TIME} THEN 'too_slow'
                         WHEN deleted THEN 'deleted_by_stewards'
                       END AS issue
                FROM `{PROJECT}.{DATASET}.laps`
                WHERE session_key = {session_key}
                  AND (lap_duration < {MIN_LAP_TIME} OR lap_duration > {MAX_LAP_TIME} OR deleted = TRUE)
            """
            invalid_df = client.query(invalid_q).to_dataframe()
            for _, row in invalid_df.iterrows():
                add_exc("invalid_lap_time", "warning", row["issue"],
                        {"driver_number": row["driver_number"], "lap_number": int(row["lap_number"])})
        except Exception as e:
            print(f"  ⚠  Check 2 error: {e}")

        # Check 3: Session-level anomalies
        try:
            stats_q = f"""
                SELECT COUNT(*) AS total_laps, COUNT(DISTINCT driver_number) AS unique_drivers
                FROM `{PROJECT}.{DATASET}.laps`
                WHERE session_key = {session_key}
            """
            stats = client.query(stats_q).to_dataframe().iloc[0]
            if stats["total_laps"] < MIN_LAPS_PER_SESSION:
                add_exc("session_anomaly", "critical", "Low lap count — possible import failure",
                        {"suggested_action": "Re-run import for this session"})
        except Exception as e:
            print(f"  ⚠  Check 3 error: {e}")

        # Check 4: Lap number gaps per driver
        try:
            gaps_q = f"""
                WITH ranked AS (
                  SELECT driver_number, lap_number,
                         LAG(lap_number) OVER (PARTITION BY driver_number ORDER BY lap_number) AS prev_lap
                  FROM `{PROJECT}.{DATASET}.laps`
                  WHERE session_key = {session_key}
                )
                SELECT driver_number, prev_lap, lap_number, (lap_number - prev_lap) AS gap_size
                FROM ranked
                WHERE lap_number - prev_lap > 1
            """
            gaps_df = client.query(gaps_q).to_dataframe()
            for _, row in gaps_df.iterrows():
                add_exc("lap_gap", "warning",
                        f"Gap of {int(row['gap_size'])} laps (#{int(row['prev_lap'])} → #{int(row['lap_number'])})",
                        {"driver_number": row["driver_number"]})
        except Exception as e:
            print(f"  ⚠  Check 4 error: {e}")

        print(f"  {year} {stype}: {len(exceptions)} exception(s) found")
        all_exceptions.extend(exceptions)

    if all_exceptions:
        exc_df = pd.DataFrame(all_exceptions)
        try:
            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            job = client.load_table_from_dataframe(
                exc_df, f"{PROJECT}.{DATASET}.data_quality_exceptions", job_config=job_config
            )
            job.result()
            print(f"  ✅  {len(exc_df)} exception(s) saved to BigQuery")
        except Exception as e:
            print(f"  ⚠  Could not save exceptions to BigQuery: {e}")
            csv_path = f"exceptions_{race.replace(' ', '_')}.csv"
            exc_df.to_csv(csv_path, index=False)
            print(f"  Exceptions saved locally: {csv_path}")
    else:
        print("  ✅  No exceptions found")

    return all_exceptions


# ── Step 8: Update laps_unified ───────────────────────────────────────────────

def update_laps_unified(client, loaded_sessions):
    for (year, stype), session in loaded_sessions.items():
        session_key = generate_session_key(year, session.event["EventName"], stype)

        derive_q = f"""
            WITH telemetry_laps AS (
              SELECT session_key, driver_number, lap_number,
                     COUNT(*) AS telemetry_points,
                     MAX(speed) AS max_speed,
                     AVG(CASE WHEN speed > 0 THEN speed END) AS avg_speed
              FROM `{PROJECT}.{DATASET}.telemetry`
              WHERE session_key = {session_key}
              GROUP BY session_key, driver_number, lap_number
            )
            SELECT
              lm.session_key AS session_id,
              lm.driver_number AS driver_id,
              lm.driver_code,
              lm.lap_number,
              CAST(ROUND(lm.lap_duration * 1000) AS INT64) AS lap_time_ms,
              CAST(ROUND(lm.sector_1_time * 1000) AS INT64) AS sector1_ms,
              CAST(ROUND(lm.sector_2_time * 1000) AS INT64) AS sector2_ms,
              CAST(ROUND(lm.sector_3_time * 1000) AS INT64) AS sector3_ms,
              lm.session_type,
              lm.event_name AS race_name,
              lm.season,
              lm.team,
              lm.position,
              lm.compound,
              lm.tyre_age_laps AS tyre_life,
              lm.stint_number AS stint,
              lm.is_personal_best,
              lm.deleted,
              tl.max_speed,
              tl.avg_speed,
              CASE
                WHEN tl.telemetry_points >= 50 THEN 'validated'
                WHEN tl.telemetry_points > 0  THEN 'suspect'
                ELSE 'legacy'
              END AS data_quality,
              CASE WHEN tl.telemetry_points > 0 THEN TRUE ELSE FALSE END AS telemetry_available,
              CURRENT_TIMESTAMP() AS imported_at
            FROM `{PROJECT}.{DATASET}.laps` lm
            LEFT JOIN telemetry_laps tl
              ON lm.session_key = tl.session_key
             AND lm.driver_number = tl.driver_number
             AND lm.lap_number = tl.lap_number
            WHERE lm.session_key = {session_key}
        """

        try:
            unified_df = client.query(derive_q).to_dataframe()

            delete_q = f"DELETE FROM `{PROJECT}.{DATASET}.laps_unified` WHERE session_id = {session_key}"
            client.query(delete_q).result()

            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            job = client.load_table_from_dataframe(
                unified_df, f"{PROJECT}.{DATASET}.laps_unified", job_config=job_config
            )
            job.result()
            print(f"  ✅  {year} {stype}: {len(unified_df)} laps written to laps_unified")
        except Exception as e:
            print(f"  ⚠  {year} {stype}: laps_unified update failed — {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Import F1 telemetry from FastF1 into BigQuery"
    )
    parser.add_argument(
        "--year", "-y", type=int, nargs="+", required=True,
        help="Season year(s), e.g. --year 2025 or --year 2024 2025"
    )
    parser.add_argument(
        "--race", "-r", type=str, required=True,
        help='Event name, e.g. "Australian Grand Prix"'
    )
    parser.add_argument(
        "--session", "-s", nargs="+",
        choices=["FP1", "FP2", "FP3", "Q", "SQ", "R"],
        default=["R"],
        help="Session type(s), default: R"
    )
    parser.add_argument(
        "--no-skip", action="store_true",
        help="Re-import even if data already exists in BigQuery"
    )
    parser.add_argument(
        "--cache-dir", type=str, default=DEFAULT_CACHE_DIR,
        help=f"FastF1 cache directory (default: {DEFAULT_CACHE_DIR})"
    )
    parser.add_argument(
        "--skip-quality-checks", action="store_true",
        help="Skip data quality checks"
    )
    parser.add_argument(
        "--skip-unified", action="store_true",
        help="Skip updating the laps_unified table"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    years = sorted(set(args.year))
    race = args.race
    session_types = args.session
    skip_existing = not args.no_skip

    print(f"\n🏎  F1 Telemetry Import")
    print(f"   Years:    {years}")
    print(f"   Race:     {race}")
    print(f"   Sessions: {session_types}")
    print(f"   Skip existing: {skip_existing}\n")

    # FastF1 cache
    os.makedirs(args.cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(args.cache_dir)
    print(f"FastF1 cache: {args.cache_dir}")

    # BigQuery client (uses ADC or GOOGLE_APPLICATION_CREDENTIALS)
    client = bigquery.Client(project=PROJECT)
    print(f"BigQuery project: {PROJECT}\n")

    # Step 1: Check existing
    print("── Step 1: Checking existing data…")
    existing = check_existing(client, years, race, session_types) if skip_existing else {}

    # Step 2: Load sessions
    print("\n── Step 2: Loading FastF1 sessions…")
    loaded_sessions = load_sessions(years, race, session_types, skip_existing, existing)
    if not loaded_sessions:
        print("Nothing to import. Exiting.")
        sys.exit(0)

    # Step 3: Extract telemetry
    print("\n── Step 3: Extracting & resampling telemetry…")
    telemetry_df, laps_df = extract_telemetry(loaded_sessions)

    # Step 4: Upload sessions + laps
    print("\n── Step 4: Uploading sessions & laps…")
    upload_sessions_and_laps(client, loaded_sessions, laps_df, race)

    # Step 5: Upload telemetry
    print("\n── Step 5: Uploading telemetry…")
    upload_telemetry(client, telemetry_df, loaded_sessions)

    # Step 6: Verify
    print("\n── Step 6: Verifying upload…")
    verify_upload(client, years, race, session_types)

    # Step 7: Quality checks
    if not args.skip_quality_checks:
        print("\n── Step 7: Running data quality checks…")
        run_quality_checks(client, loaded_sessions, race)

    # Step 8: laps_unified
    if not args.skip_unified:
        print("\n── Step 8: Updating laps_unified…")
        update_laps_unified(client, loaded_sessions)

    print("\n✅  Import complete.\n")


if __name__ == "__main__":
    main()
