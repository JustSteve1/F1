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
import os
import sys
import warnings
from datetime import datetime, timezone

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

def _load_session_with_retries(year, race, stype, attempts=3):
    """Load a FastF1 session with retries and telemetry fallback."""
    import time

    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            session = fastf1.get_session(year, race, stype)
            try:
                session.load(telemetry=True, laps=True, weather=False)
            except Exception as tel_err:
                # Some hosts (e.g. restricted Cloud Run egress) fail car data
                # but can still load laps; retry laps-only then require telemetry
                # via get_telemetry later — fail clearly if car data missing.
                print(
                    f"  ⚠️  {year} {stype}: telemetry load failed "
                    f"(attempt {attempt}/{attempts}): {str(tel_err)[:160]}"
                )
                session = fastf1.get_session(year, race, stype)
                session.load(telemetry=False, laps=True, weather=False)
                # Probe one lap for car telemetry availability
                if len(session.laps) == 0:
                    raise RuntimeError("no laps found after laps-only load") from tel_err
                probe = session.laps.iloc[0]
                try:
                    telem = probe.get_telemetry()
                    if telem is None or len(telem) == 0:
                        raise RuntimeError(
                            "telemetry unavailable on this host "
                            f"(laps loaded but car data empty): {tel_err}"
                        )
                except Exception as probe_err:
                    raise RuntimeError(
                        "telemetry unavailable on this host "
                        f"(laps loaded but get_telemetry failed): {probe_err}"
                    ) from probe_err
            if len(session.laps) == 0:
                raise RuntimeError("no laps found")
            return session
        except Exception as e:
            last_err = e
            msg = str(e)
            print(f"  ❌  {year} {stype}: attempt {attempt}/{attempts}: {msg[:200]}")
            if attempt < attempts:
                time.sleep(2 ** attempt)
    assert last_err is not None
    raise last_err


def load_sessions(years, race, session_types, skip_existing, existing):
    loaded = {}
    errors = []
    for year in years:
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
                errors.append(err)
                print(f"  ❌  {err[:240]}")
    if not loaded and errors:
        # Surface root cause instead of opaque "no sessions loaded"
        raise RuntimeError(
            "Nothing to import — FastF1 load failed: " + " | ".join(errors)[:800]
        )
    return loaded


# ── Step 3: Resample telemetry ────────────────────────────────────────────────

def resample_lap_telemetry(lap, interval_sec=TELEMETRY_INTERVAL):
    try:
        telemetry = lap.get_telemetry()
        if len(telemetry) == 0:
            return []

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
                "x": safe_float(row.get("X")),
                "y": safe_float(row.get("Y")),
                "z": safe_float(row.get("Z")),
                "deceleration": round(decel, 2),
                "distance_m": round(distance_m, 2),
                "cumulative_distance": safe_float(row.get("Distance")),
            })
        return resampled
    except Exception:
        return []


def extract_telemetry(loaded_sessions):
    all_telemetry = []
    all_laps = []

    for (year, stype), session in loaded_sessions.items():
        event_name = session.event["EventName"]
        circuit = session.event.get("Location", "")
        print(f"  Extracting {year} {stype} ({len(session.laps)} laps)…")

        for _, lap in session.laps.iterrows():
            points = resample_lap_telemetry(lap)
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

    telemetry_df = pd.DataFrame(all_telemetry).drop_duplicates(
        subset=["season", "session_type", "driver_number", "lap_number", "lap_time_sec"]
    )
    laps_df = pd.DataFrame(all_laps)
    print(f"  ✅  {len(telemetry_df):,} telemetry points, {len(laps_df):,} laps extracted")
    return telemetry_df, laps_df


# ── Step 4: Upload sessions + laps ───────────────────────────────────────────

def upload_sessions_and_laps(client, loaded_sessions, laps_df, race):
    now = datetime.now(timezone.utc).isoformat()

    # Sessions
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

    errors = client.insert_rows_json(f"{PROJECT}.{DATASET}.sessions", sessions_rows)
    if errors:
        print(f"  ⚠  Session upload errors: {errors[:2]}")
    else:
        print(f"  ✅  {len(sessions_rows)} session(s) uploaded")

    # Laps — full schema (Cell 7 style)
    laps_full = []
    for (year, stype), session in loaded_sessions.items():
        sk = generate_session_key(year, session.event["EventName"], stype)
        # Dedup check
        check_q = f"""
            SELECT CONCAT(CAST(session_key AS STRING), '-', driver_number, '-', CAST(lap_number AS STRING)) as lap_id
            FROM `{PROJECT}.{DATASET}.laps`
            WHERE session_key = {sk}
        """
        try:
            existing_ids = set(client.query(check_q).to_dataframe()["lap_id"].tolist())
        except Exception:
            existing_ids = set()

        for _, lap in session.laps.iterrows():
            lap_id = f"{sk}-{lap.get('DriverNumber')}-{lap.get('LapNumber')}"
            if lap_id in existing_ids:
                continue
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
        uploaded = upload_in_batches(
            client,
            f"{PROJECT}.{DATASET}.laps",
            laps_full,
            batch_size=500,
            label="laps",
        )
        print(f"  ✅  {uploaded:,} laps uploaded")
    else:
        print("  ⏭  No new laps to upload")


# ── Step 5: Upload telemetry ──────────────────────────────────────────────────

def upload_telemetry(client, telemetry_df, loaded_sessions):
    now = datetime.now(timezone.utc).isoformat()
    telemetry_df = telemetry_df.copy()
    telemetry_df["imported_at"] = now
    telemetry_df["date"] = now
    telemetry_df["session_key"] = telemetry_df.apply(
        lambda r: generate_session_key(r["season"], r["event_name"], r["session_type"]), axis=1
    )
    telemetry_df["meeting_key"] = telemetry_df["session_key"]

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
    upload_df = upload_df.where(pd.notnull(upload_df), None)
    rows = upload_df.to_dict("records")

    uploaded = upload_in_batches(client, f"{PROJECT}.{DATASET}.telemetry", rows, label="telemetry points")
    print(f"  ✅  {uploaded:,} telemetry points uploaded")


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
