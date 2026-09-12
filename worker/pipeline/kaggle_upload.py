"""
Kaggle Upload — F1 lap data from BigQuery → Kaggle dataset

Reads the 13-column `for_kaggle_export` table (2 Hz telemetry JSON already
on each lap), merges with the current Kaggle CSV, and uploads a new version.

Usage:
    python kaggle_upload.py

Auth:
    BigQuery : gcloud auth application-default login
    Kaggle   : KAGGLE_API_TOKEN (preferred) OR ~/.kaggle/kaggle.json
               OR KAGGLE_USERNAME + KAGGLE_KEY

Output file on Kaggle: "All Laps - {DD Month YYYY}.csv"
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import kagglehub
import pandas as pd
from google.cloud import bigquery
from kaggle.api.kaggle_api_extended import KaggleApi

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT        = os.environ.get("BQ_PROJECT",      "f1-data-library")
DATASET        = os.environ.get("BQ_DATASET",      "f1_data_library_DS")
KAGGLE_DATASET = os.environ.get("KAGGLE_DATASET",  "stevefza/f1-2026-bahrain-testing-day-2")

from kaggle_export import (  # noqa: E402
    KAGGLE_EXPORT_COLUMNS,
    fetch_kaggle_export,
    merge_kaggle_csv,
    table_ref as kaggle_export_table_ref,
)


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


# ── Step 2: Read for_kaggle_export ────────────────────────────────────────────

def fetch_bq_laps(client: bigquery.Client) -> pd.DataFrame:
    """Fetch the 13-column Kaggle export table (already includes 2 Hz telemetry JSON)."""
    print(f"  Querying `{kaggle_export_table_ref()}`…")
    df = fetch_kaggle_export(client)
    print(f"  ✅  {len(df):,} laps fetched from {kaggle_export_table_ref()}")
    return df


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

    # Step 2: Fetch for_kaggle_export
    print("\n── Step 2: Fetch for_kaggle_export…")
    export_df = fetch_bq_laps(bq)

    if export_df.empty:
        print("  No rows in for_kaggle_export. Nothing to upload.")
        return

    # Step 3: Merge — replace Kaggle rows whose keys exist in the export table
    print("\n── Step 3: Merge with existing Kaggle CSV…")
    combined = merge_kaggle_csv(existing_df, export_df)
    if set(KAGGLE_EXPORT_COLUMNS).issubset(combined.columns):
        combined = combined[KAGGLE_EXPORT_COLUMNS]
    print(f"  ✅  Total rows for upload: {len(combined):,}")

    # Step 4: Upload to Kaggle (kagglehub)
    print("\n── Step 4: Upload to Kaggle…")
    upload_to_kaggle(combined)

    print("\n✅  Kaggle upload complete.\n")


if __name__ == "__main__":
    main()
