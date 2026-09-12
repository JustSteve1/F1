"""Build and load the 13-column Kaggle export table from FastF1 (2 Hz)."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import SchemaField, Table

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
TABLE_NAME = "for_kaggle_export"

# Match the published Kaggle CSV density (0.5 s). 10 Hz can be a later flag.
TELEMETRY_INTERVAL_KAGGLE = float(os.environ.get("TELEMETRY_INTERVAL_KAGGLE", "0.5"))

KAGGLE_EXPORT_COLUMNS = [
    "season",
    "event_name",
    "circuit",
    "session_type",
    "driver",
    "driver_number",
    "lap_number",
    "lap_time",
    "lap_duration",
    "compound",
    "tyre_age",
    "stint_number",
    "telemetry",
]

KAGGLE_EXPORT_SCHEMA = [
    SchemaField("season", "INT64"),
    SchemaField("event_name", "STRING"),
    SchemaField("circuit", "STRING"),
    SchemaField("session_type", "STRING"),
    SchemaField("driver", "STRING"),
    SchemaField("driver_number", "INT64"),
    SchemaField("lap_number", "INT64"),
    SchemaField("lap_time", "STRING"),
    SchemaField("lap_duration", "FLOAT64"),
    SchemaField("compound", "STRING"),
    SchemaField("tyre_age", "INT64"),
    SchemaField("stint_number", "INT64"),
    SchemaField("telemetry", "STRING"),
]

DEDUP_COLS = [
    "season",
    "event_name",
    "session_type",
    "driver_number",
    "lap_number",
]


def table_ref() -> str:
    return f"{PROJECT}.{DATASET}.{TABLE_NAME}"


def format_lap_time(seconds) -> str:
    """Convert float seconds to 'M:SS.mmm', matching the public Kaggle file."""
    if seconds is None or (isinstance(seconds, float) and pd.isna(seconds)):
        return "0:00.000"
    try:
        total = float(seconds)
    except (TypeError, ValueError):
        return "0:00.000"
    if pd.isna(total):
        return "0:00.000"
    sign = "-" if total < 0 else ""
    total = abs(total)
    minutes = int(total // 60)
    return f"{sign}{minutes}:{total - minutes * 60:06.3f}"


def _is_kaggle_tick(lap_time_sec: float, interval_sec: float = TELEMETRY_INTERVAL_KAGGLE) -> bool:
    """Keep published 2 Hz ticks (0.0, 0.5, 1.0, …) even if the frame is denser."""
    if interval_sec <= 0:
        return True
    tenths = int(round(float(lap_time_sec) * 10))
    step = int(round(interval_sec * 10))
    if step <= 0:
        return True
    return tenths % step == 0


def build_telemetry_json(points_df: pd.DataFrame) -> str:
    """Pack per-lap samples into the Kaggle JSON array string (2 Hz by default)."""
    if points_df is None or len(points_df) == 0:
        return "[]"
    records = []
    ordered = points_df.sort_values("lap_time_sec") if "lap_time_sec" in points_df.columns else points_df
    for _, row in ordered.iterrows():
        t_raw = row.get("lap_time_sec")
        if pd.notna(t_raw) and not _is_kaggle_tick(float(t_raw)):
            continue
        record = {
            "t": round(float(row["lap_time_sec"]), 1) if pd.notna(row.get("lap_time_sec")) else None,
            "speed": int(row["speed"]) if pd.notna(row.get("speed")) else None,
            "throttle": int(row["throttle"]) if pd.notna(row.get("throttle")) else None,
            "brake": int(row["brake"]) if pd.notna(row.get("brake")) else None,
            "gear": int(row["gear"]) if pd.notna(row.get("gear")) else None,
            "rpm": int(row["rpm"]) if pd.notna(row.get("rpm")) else None,
            "drs": int(row["drs"]) if pd.notna(row.get("drs")) else None,
            "x": round(float(row["x"]), 1) if pd.notna(row.get("x")) else None,
            "y": round(float(row["y"]), 1) if pd.notna(row.get("y")) else None,
            "z": round(float(row["z"]), 1) if pd.notna(row.get("z")) else None,
        }
        records.append({k: v for k, v in record.items() if v is not None})
    return json.dumps(records, separators=(",", ":"))


def ensure_kaggle_export_table(client) -> str:
    """CREATE TABLE IF NOT EXISTS with STRING telemetry (never BQ JSON)."""
    from google.api_core.exceptions import NotFound

    ref = table_ref()
    try:
        table = client.get_table(ref)
    except NotFound:
        table = Table(ref, schema=KAGGLE_EXPORT_SCHEMA)
        table.clustering_fields = ["season", "event_name", "session_type"]
        client.create_table(table, exists_ok=True)
        return ref

    json_cols = [
        f.name
        for f in table.schema
        if (getattr(f, "field_type", None) or "").upper() == "JSON"
    ]
    if json_cols:
        raise RuntimeError(
            f"{ref} has JSON column(s) {json_cols}; Kaggle export requires "
            "STRING telemetry. Recreate the table "
            "(DROP + sql/create_for_kaggle_export.sql). "
            "Do not rewrite existing telemetry JSON blobs."
        )
    return ref


def check_existing_kaggle_export(client, years, race, session_types) -> dict:
    """Sessions already present in for_kaggle_export."""
    if not years or not session_types:
        return {}
    query = f"""
        SELECT DISTINCT season, session_type
        FROM `{table_ref()}`
        WHERE season IN UNNEST(@years)
          AND event_name = @race
          AND session_type IN UNNEST(@sessions)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("years", "INT64", [int(y) for y in years]),
            bigquery.ScalarQueryParameter("race", "STRING", race),
            bigquery.ArrayQueryParameter(
                "sessions", "STRING", [str(s) for s in session_types]
            ),
        ]
    )
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
        return {(int(r["season"]), r["session_type"]): True for _, r in df.iterrows()}
    except Exception:
        return {}


def delete_kaggle_export_rows(client, years, race, session_types, *, log=print) -> int:
    if not years or not session_types:
        return 0
    query = f"""
        DELETE FROM `{table_ref()}`
        WHERE season IN UNNEST(@years)
          AND event_name = @race
          AND session_type IN UNNEST(@sessions)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("years", "INT64", [int(y) for y in years]),
            bigquery.ScalarQueryParameter("race", "STRING", race),
            bigquery.ArrayQueryParameter(
                "sessions", "STRING", [str(s) for s in session_types]
            ),
        ]
    )
    job = client.query(query, job_config=job_config)
    job.result()
    affected = job.num_dml_affected_rows
    log(
        f"Deleted {affected if affected is not None else '?'} "
        f"{TABLE_NAME} row(s) for {race} {list(session_types)} "
        f"(job {job.job_id})"
    )
    return int(affected or 0)


def _int_or_none(val) -> int | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _float_or_none(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _lap_duration_seconds(val) -> float | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, "total_seconds"):
        return float(val.total_seconds())
    return _float_or_none(val)


def _str_or_none(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    text = str(val).strip()
    return text or None


def _telemetry_groups(telemetry_df: pd.DataFrame):
    if telemetry_df is None or len(telemetry_df) == 0:
        return None
    tel = telemetry_df.copy()
    tel["_k"] = list(
        zip(
            pd.to_numeric(tel["season"], errors="coerce").fillna(-1).astype(int),
            tel["event_name"].astype(str),
            tel["session_type"].astype(str),
            pd.to_numeric(tel["driver_number"], errors="coerce").fillna(-1).astype(int),
            pd.to_numeric(tel["lap_number"], errors="coerce").fillna(-1).astype(int),
        )
    )
    return tel.groupby("_k", sort=False)


def build_kaggle_export_frame(loaded_sessions, telemetry_df: pd.DataFrame) -> pd.DataFrame:
    """One Kaggle-shaped row per FastF1 lap, telemetry JSON at 2 Hz."""
    grouped = _telemetry_groups(telemetry_df)
    rows: list[dict[str, Any]] = []

    for (year, stype), session in loaded_sessions.items():
        event_name = session.event["EventName"]
        circuit = session.event.get("Location") or event_name
        for _, lap in session.laps.iterrows():
            driver_number = _int_or_none(lap.get("DriverNumber"))
            lap_number = _int_or_none(lap.get("LapNumber"))
            lap_duration = _lap_duration_seconds(lap.get("LapTime"))

            tel_json = "[]"
            if grouped is not None and driver_number is not None and lap_number is not None:
                key = (int(year), str(event_name), str(stype), int(driver_number), int(lap_number))
                try:
                    group = grouped.get_group(key)
                    tel_json = build_telemetry_json(group)
                except KeyError:
                    tel_json = "[]"

            rows.append(
                {
                    "season": int(year),
                    "event_name": event_name,
                    "circuit": circuit,
                    "session_type": stype,
                    "driver": _str_or_none(lap.get("Driver")),
                    "driver_number": driver_number,
                    "lap_number": lap_number,
                    "lap_time": format_lap_time(lap_duration),
                    "lap_duration": lap_duration,
                    "compound": _str_or_none(lap.get("Compound")),
                    "tyre_age": _int_or_none(lap.get("TyreLife")),
                    "stint_number": _int_or_none(lap.get("Stint")),
                    "telemetry": tel_json,
                }
            )

    if not rows:
        return pd.DataFrame(columns=KAGGLE_EXPORT_COLUMNS)
    return pd.DataFrame(rows)[KAGGLE_EXPORT_COLUMNS]


def upload_kaggle_export(
    client,
    loaded_sessions,
    telemetry_df: pd.DataFrame,
    *,
    years,
    race: str,
    session_types,
    log=print,
    job_id: str | None = None,
) -> dict:
    """Delete-replace this event/sessions in for_kaggle_export, then load 13-col rows."""
    ensure_kaggle_export_table(client)
    df = build_kaggle_export_frame(loaded_sessions, telemetry_df)
    delete_kaggle_export_rows(client, years, race, session_types, log=log)
    if df.empty:
        log("No Kaggle export rows to load")
        return {"rows": 0, "bq_job_id": None, "method": "skip"}

    from f1_telemetry_import import load_dataframe

    result = load_dataframe(
        client,
        table_ref(),
        df,
        log=log,
        job_id=job_id,
        label="kaggle export laps",
    )
    log(f"{result['rows']:,} kaggle export laps uploaded")
    return result


def fetch_kaggle_export(client) -> pd.DataFrame:
    """Read the 13-column table for Kaggle publish."""
    cols = ", ".join(KAGGLE_EXPORT_COLUMNS)
    query = f"""
        SELECT {cols}
        FROM `{table_ref()}`
        WHERE driver IS NOT NULL
          AND lap_number IS NOT NULL
    """
    df = client.query(query).to_dataframe()
    return df


def _dedup_key_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["event_name"] = out["event_name"].astype(str)
    out["session_type"] = out["session_type"].astype(str)
    out["driver_number"] = pd.to_numeric(out["driver_number"], errors="coerce")
    out["lap_number"] = pd.to_numeric(out["lap_number"], errors="coerce")
    return out


def merge_kaggle_csv(existing_df: pd.DataFrame, export_df: pd.DataFrame) -> pd.DataFrame:
    """Keep Kaggle-only history; replace any key that exists in for_kaggle_export."""
    empty = pd.DataFrame(columns=KAGGLE_EXPORT_COLUMNS)
    if export_df is None or export_df.empty:
        return existing_df.copy() if existing_df is not None and not existing_df.empty else empty

    export_cols = [c for c in KAGGLE_EXPORT_COLUMNS if c in export_df.columns]
    export = export_df[export_cols].copy()

    if existing_df is None or existing_df.empty:
        combined = export
    else:
        shared = [c for c in export.columns if c in existing_df.columns]
        existing = existing_df[shared].copy()
        export_keyed = _dedup_key_frame(export)
        existing_keyed = _dedup_key_frame(existing)
        export_keys = set(
            zip(
                export_keyed["season"],
                export_keyed["event_name"],
                export_keyed["session_type"],
                export_keyed["driver_number"],
                export_keyed["lap_number"],
            )
        )
        keep = [
            (
                row.season,
                row.event_name,
                row.session_type,
                row.driver_number,
                row.lap_number,
            )
            not in export_keys
            for row in existing_keyed.itertuples(index=False)
        ]
        combined = pd.concat([existing[keep], export], ignore_index=True)

    combined = combined.drop_duplicates(subset=DEDUP_COLS).sort_values(DEDUP_COLS)
    return combined.reset_index(drop=True)


def run_kaggle_export_quality_checks(client, years, race, session_types, *, log=print) -> list[dict]:
    """Flag missing identity, duration, or empty telemetry blobs."""
    from datetime import datetime

    from f1_telemetry_import import DATASET as _DS
    from f1_telemetry_import import PROJECT as _P
    from f1_telemetry_import import generate_session_key

    exceptions: list[dict] = []
    now = datetime.utcnow().isoformat()
    query = f"""
        SELECT
            season,
            event_name,
            session_type,
            driver_number,
            lap_number,
            CASE
              WHEN driver IS NULL OR driver = '' THEN 'missing_driver'
              WHEN lap_number IS NULL THEN 'missing_lap_number'
              WHEN lap_duration IS NULL THEN 'missing_lap_duration'
              WHEN telemetry IS NULL OR telemetry = '[]' THEN 'empty_telemetry'
            END AS issue
        FROM `{table_ref()}`
        WHERE season IN UNNEST(@years)
          AND event_name = @race
          AND session_type IN UNNEST(@sessions)
          AND (
            driver IS NULL OR driver = ''
            OR lap_number IS NULL
            OR lap_duration IS NULL
            OR telemetry IS NULL OR telemetry = '[]'
          )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("years", "INT64", [int(y) for y in years]),
            bigquery.ScalarQueryParameter("race", "STRING", race),
            bigquery.ArrayQueryParameter(
                "sessions", "STRING", [str(s) for s in session_types]
            ),
        ]
    )
    try:
        df = client.query(query, job_config=job_config).to_dataframe()
    except Exception as exc:
        log(f"Kaggle export quality query failed: {exc}")
        return []

    for _, row in df.iterrows():
        year = int(row["season"])
        stype = str(row["session_type"])
        session_key = generate_session_key(year, str(row["event_name"]), stype)
        exceptions.append(
            {
                "exception_id": f"{session_key}-kaggle-{len(exceptions) + 1}",
                "detected_at": now,
                "severity": "warning",
                "category": "kaggle_export",
                "description": row["issue"],
                "season": year,
                "event_name": row["event_name"],
                "session_type": stype,
                "session_key": session_key,
                "driver_number": row["driver_number"],
                "lap_number": int(row["lap_number"]) if pd.notna(row["lap_number"]) else None,
                "suggested_action": "Re-seed FastF1 cache and re-run Kaggle export with noSkip",
            }
        )

    log(f"{len(exceptions)} kaggle-export quality exception(s)")
    if exceptions:
        exc_df = pd.DataFrame(exceptions)
        try:
            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            client.load_table_from_dataframe(
                exc_df, f"{_P}.{_DS}.data_quality_exceptions", job_config=job_config
            ).result()
        except Exception as exc:
            log(f"Could not save kaggle-export exceptions: {exc}")
    return exceptions
