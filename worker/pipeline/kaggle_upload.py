"""
Kaggle Upload — F1 lap data from BigQuery → Kaggle dataset

Pulls laps from the laps_for_export view, replaces matching Kaggle rows with
that view, keeps rows that exist only on Kaggle, and uploads one cumulative
file as a new dataset version.

Usage:
    python kaggle_upload.py

Auth:
    BigQuery : gcloud auth application-default login
    Kaggle   : KAGGLE_API_TOKEN (preferred) OR ~/.kaggle/kaggle.json
               OR KAGGLE_USERNAME + KAGGLE_KEY

Output file on Kaggle: "All Laps - {DD Month YYYY}.csv"
"""

import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import kagglehub
import pandas as pd
from google.cloud import bigquery
from kaggle.api.kaggle_api_extended import KaggleApi

import kaggle_merge

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT        = os.environ.get("BQ_PROJECT",      "f1-data-library")
DATASET        = os.environ.get("BQ_DATASET",      "f1_data_library_DS")
KAGGLE_DATASET = os.environ.get("KAGGLE_DATASET",  "stevefza/f1-2026-bahrain-testing-day-2")

# Telemetry downsampled to 0.5s intervals for Kaggle (matches existing file format)
TELEMETRY_INTERVAL_KAGGLE = 0.5

# ── Helpers ───────────────────────────────────────────────────────────────────

def format_lap_time(seconds) -> str:
    """Convert float seconds to 'M:SS.mmm' string, matching Kaggle file format."""
    if pd.isna(seconds) or seconds is None:
        return "0:00.000"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}"


def build_telemetry_json(points_df: pd.DataFrame) -> str:
    """
    Convert a per-lap telemetry DataFrame (already filtered to 0.5s intervals)
    into the JSON array string expected by Kaggle.
    """
    records = []
    for _, row in points_df.iterrows():
        record = {
            "t":        round(float(row["lap_time_sec"]), 1),
            "speed":    int(row["speed"])    if pd.notna(row.get("speed"))    else None,
            "throttle": int(row["throttle"]) if pd.notna(row.get("throttle")) else None,
            "brake":    int(row["brake"])    if pd.notna(row.get("brake"))    else None,
            "gear":     int(row["gear"])     if pd.notna(row.get("gear"))     else None,
            "rpm":      int(row["rpm"])      if pd.notna(row.get("rpm"))      else None,
            "drs":      int(row["drs"])      if pd.notna(row.get("drs"))      else None,
            "x":        round(float(row["x"]), 1) if pd.notna(row.get("x")) else None,
            "y":        round(float(row["y"]), 1) if pd.notna(row.get("y")) else None,
            "z":        round(float(row["z"]), 1) if pd.notna(row.get("z")) else None,
        }
        records.append({k: v for k, v in record.items() if v is not None})
    return json.dumps(records, separators=(",", ":"))


# ── Step 1: Download current Kaggle CSV ───────────────────────────────────────

def download_current_kaggle_data(api: KaggleApi) -> pd.DataFrame:
    """Download latest Kaggle dataset version, return combined DataFrame of all 'All Laps' CSVs."""
    print("  Downloading current Kaggle dataset…")
    tmp_dir = tempfile.mkdtemp(prefix="kaggle_dl_")
    try:
        api.dataset_download_files(KAGGLE_DATASET, path=tmp_dir, unzip=True)

        all_dfs = []
        for fname in os.listdir(tmp_dir):
            if fname.endswith(".csv") and "All Laps" in fname:
                fpath = os.path.join(tmp_dir, fname)
                df = pd.read_csv(fpath, low_memory=False)
                all_dfs.append(df)
                print(f"  Found: {fname} ({len(df):,} rows)")

        if not all_dfs:
            print("  No existing 'All Laps' CSV found — starting fresh.")
            return pd.DataFrame()

        combined = pd.concat(all_dfs, ignore_index=True)
        # Normalise types for dedup comparison
        for col in ["season", "driver_number", "lap_number"]:
            if col in combined.columns:
                combined[col] = pd.to_numeric(combined[col], errors="coerce")
        combined = combined.drop_duplicates(
            subset=["season", "event_name", "session_type", "driver_number", "lap_number"]
        )
        print(f"  ✅  {len(combined):,} existing rows loaded")
        return combined
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Step 2: Query BigQuery for all laps ───────────────────────────────────────

def fetch_bq_laps(client: bigquery.Client) -> pd.DataFrame:
    """Fetch the Kaggle-shaped laps_for_export view.

    A session comes entirely from laps_all_live or entirely from
    laps_all_legacy. Telemetry is never taken from the other source.
    """
    print("  Querying BigQuery laps_for_export…")
    columns = ", ".join(kaggle_merge.KAGGLE_COLUMNS)
    query = f"SELECT {columns} FROM `{PROJECT}.{DATASET}.laps_for_export`"
    df = client.query(query).to_dataframe()
    print(f"  ✅  {len(df):,} laps fetched from BigQuery")
    return df


def _records(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict("records")


def combine_kaggle_export(existing_df: pd.DataFrame, view_df: pd.DataFrame) -> pd.DataFrame:
    """Replace Kaggle rows with the view. Keep Kaggle rows the view does not have."""
    rows = kaggle_merge.combine_kaggle_rows(_records(existing_df), _records(view_df))
    columns = list(kaggle_merge.KAGGLE_COLUMNS)
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows)[columns]


def export_unchanged(existing_df: pd.DataFrame, combined_df: pd.DataFrame) -> bool:
    return kaggle_merge.rows_unchanged(_records(existing_df), _records(combined_df))


# ── Step 3: Find new rows ─────────────────────────────────────────────────────

def find_new_laps(bq_df: pd.DataFrame, existing_df: pd.DataFrame) -> pd.DataFrame:
    """Return rows in bq_df that are not already in existing_df."""
    if existing_df.empty:
        return bq_df

    DEDUP_COLS = ["season", "event_name", "session_type", "driver_number", "lap_number"]

    existing_keys = set(
        zip(
            existing_df["season"].astype(float),
            existing_df["event_name"].astype(str),
            existing_df["session_type"].astype(str),
            existing_df["driver_number"].astype(float),
            existing_df["lap_number"].astype(float),
        )
    )

    mask = ~bq_df.apply(
        lambda r: (
            float(r["season"]),
            str(r["event_name"]),
            str(r["session_type"]),
            float(r["driver_number"]),
            float(r["lap_number"]),
        )
        in existing_keys,
        axis=1,
    )

    new_df = bq_df[mask].copy()
    print(f"  ✅  {len(new_df):,} new laps to append ({len(bq_df) - len(new_df):,} already on Kaggle)")
    return new_df


# ── Step 4: Fetch telemetry for new laps ─────────────────────────────────────

def fetch_telemetry_for_laps(client: bigquery.Client, new_laps: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch telemetry from BigQuery for the new laps only, downsampled to 0.5s intervals.
    Returns a DataFrame grouped by (session_key, driver_number, lap_number).
    """
    if new_laps.empty:
        return pd.DataFrame()

    session_keys = new_laps["session_key"].dropna().unique().tolist()
    if not session_keys:
        return pd.DataFrame()

    keys_str = ", ".join(str(int(k)) for k in session_keys)

    print(f"  Querying telemetry for {len(session_keys)} session(s)…")

    # Filter to 0.5s intervals: lap_time_sec rounded to 1 decimal, keep only x.0 and x.5
    query = f"""
        SELECT
            session_key,
            CAST(driver_number AS INT64) AS driver_number,
            CAST(lap_number    AS INT64) AS lap_number,
            lap_time_sec,
            speed,
            CAST(throttle AS INT64) AS throttle,
            CAST(brake    AS INT64) AS brake,
            gear,
            rpm,
            drs,
            x, y, z
        FROM `{PROJECT}.{DATASET}.telemetry`
        WHERE session_key IN ({keys_str})
          AND MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0
        ORDER BY session_key, driver_number, lap_number, lap_time_sec
    """
    df = client.query(query).to_dataframe()
    print(f"  ✅  {len(df):,} telemetry points fetched")
    return df


# ── Step 5: Build Kaggle rows ─────────────────────────────────────────────────

def build_kaggle_rows(new_laps: pd.DataFrame, telemetry_df: pd.DataFrame) -> pd.DataFrame:
    """Combine lap metadata and telemetry JSON into Kaggle-format rows."""

    rows = []
    tel_grouped = (
        telemetry_df.groupby(["session_key", "driver_number", "lap_number"])
        if not telemetry_df.empty
        else {}
    )

    for _, lap in new_laps.iterrows():
        sk  = lap["session_key"]
        dn  = int(lap["driver_number"])
        ln  = int(lap["lap_number"])

        # Build telemetry JSON
        tel_json = "[]"
        if not telemetry_df.empty:
            try:
                group = tel_grouped.get_group((sk, dn, ln))
                tel_json = build_telemetry_json(group)
            except KeyError:
                tel_json = "[]"

        rows.append({
            "season":       int(lap["season"]),
            "event_name":   lap["event_name"],
            "circuit":      lap["circuit"],
            "session_type": lap["session_type"],
            "driver":       lap["driver"],
            "driver_number": dn,
            "lap_number":   ln,
            "lap_time":     format_lap_time(lap["lap_duration"]),
            "lap_duration": lap["lap_duration"] if pd.notna(lap["lap_duration"]) else None,
            "compound":     lap["compound"] if pd.notna(lap.get("compound")) else None,
            "tyre_age":     int(lap["tyre_age"]) if pd.notna(lap.get("tyre_age")) else None,
            "stint_number": int(lap["stint_number"]) if pd.notna(lap.get("stint_number")) else None,
            "telemetry":    tel_json,
        })

    return pd.DataFrame(rows)


def ensure_kaggle_auth() -> None:
    """Ensure kagglehub/kaggle can authenticate (prefer KAGGLE_API_TOKEN)."""
    if os.environ.get("KAGGLE_API_TOKEN", "").strip():
        return
    if Path(os.path.expanduser("~/.kaggle/access_token")).is_file():
        return
    if Path(os.path.expanduser("~/.kaggle/kaggle.json")).is_file():
        return
    # Materialize legacy env vars into kaggle.json for kagglehub Option 5
    user = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()
    if user and key:
        kdir = Path(os.path.expanduser("~/.kaggle"))
        kdir.mkdir(parents=True, exist_ok=True)
        cfg = kdir / "kaggle.json"
        if not cfg.is_file():
            cfg.write_text(json.dumps({"username": user, "key": key}))
            cfg.chmod(0o600)
        return
    raise RuntimeError(
        "Kaggle credentials not found. Set KAGGLE_API_TOKEN "
        "(preferred) or KAGGLE_USERNAME+KAGGLE_KEY / ~/.kaggle/kaggle.json"
    )


# ── Step 6: Upload to Kaggle ──────────────────────────────────────────────────

def upload_to_kaggle(combined_df: pd.DataFrame):
    """Save combined CSV and upload as a new Kaggle dataset version via kagglehub."""
    ensure_kaggle_auth()
    today = datetime.now().strftime("%-d %B %Y")   # e.g. "30 April 2026"
    filename = f"All Laps - {today}.csv"

    tmp_dir = tempfile.mkdtemp(prefix="kaggle_upload_")
    try:
        out_path = os.path.join(tmp_dir, filename)
        combined_df.to_csv(out_path, index=False)
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"  Saved: {filename} ({size_mb:.1f} MB, {len(combined_df):,} rows)")

        notes = f"Auto-update: {len(combined_df):,} laps as of {today}"
        print(f"  Uploading via kagglehub → kaggle.com/datasets/{KAGGLE_DATASET}…")
        kagglehub.dataset_upload(
            KAGGLE_DATASET,
            tmp_dir,
            version_notes=notes,
        )
        print(f"  ✅  Uploaded as new version — {filename}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n📤  F1 → Kaggle Upload")
    print(f"    BigQuery : {PROJECT}.{DATASET}")
    print(f"    Kaggle   : {KAGGLE_DATASET}\n")

    ensure_kaggle_auth()
    api = KaggleApi()
    api.authenticate()
    print("  ✅  Kaggle authenticated\n")

    # BigQuery client
    bq = bigquery.Client(project=PROJECT)

    # Step 1: Download existing Kaggle data
    print("── Step 1: Download existing Kaggle data…")
    existing_df = download_current_kaggle_data(api)

    # Step 2: Fetch the Kaggle view. Batch laps win over laps_live inside the view.
    print("\n── Step 2: Fetch laps from BigQuery…")
    view_df = fetch_bq_laps(bq)

    if view_df.empty and existing_df.empty:
        print("  No laps in BigQuery. Nothing to upload.")
        return

    # Step 3: View rows replace the same lap already on Kaggle.
    print("\n── Step 3: Merge with the current Kaggle file…")
    combined = combine_kaggle_export(existing_df, view_df)
    if export_unchanged(existing_df, combined):
        print("  Nothing new to upload. Kaggle dataset is already up to date.")
        return

    print(f"  ✅  Total rows for upload: {len(combined):,}")

    # Step 6: Upload to Kaggle (kagglehub)
    print("\n── Step 6: Upload to Kaggle…")
    upload_to_kaggle(combined)

    print("\n✅  Kaggle upload complete.\n")


if __name__ == "__main__":
    main()
