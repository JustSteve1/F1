"""
Kaggle Upload — F1 lap data from BigQuery → Kaggle dataset

Pulls all laps + telemetry from BigQuery, deduplicates against the current
Kaggle CSV, appends only new rows, and uploads a single cumulative file as
a new dataset version with usability metadata.

Usage:
    python kaggle_upload.py
    python kaggle_upload.py --republish

Auth:
    BigQuery : gcloud auth application-default login
    Kaggle   : KAGGLE_API_TOKEN (preferred) OR ~/.kaggle/kaggle.json
               OR KAGGLE_USERNAME + KAGGLE_KEY

Output file on Kaggle: all_laps.csv
Dataset: stevefza/f1-2026-bahrain-testing-day-2 (id 9485317)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from kaggle.api.kaggle_api_extended import KaggleApi

from kaggle_metadata import (
    KAGGLE_CSV_NAME,
    KAGGLE_DATASET_LEGACY,
    build_dataset_metadata,
    dataset_handle_candidates,
    env_flag,
    is_kaggle_laps_csv,
    kaggle_dataset,
    kaggle_license_candidates,
    load_metadata_file,
    require_existing_dataset_id,
    write_metadata_file,
)

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
KAGGLE_DATASET = kaggle_dataset()

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

def resolve_dataset_handle(api: KaggleApi) -> str:
    """Prefer the new slug; fall back to the live listing until Kaggle Settings is renamed."""
    last_error: Exception | None = None
    for ref in dataset_handle_candidates():
        try:
            api.dataset_status(ref)
            return ref
        except Exception as exc:  # noqa: BLE001 — try the next public handle
            last_error = exc
            print(f"  Kaggle handle {ref} not reachable ({exc})")
    if last_error is not None:
        print(f"  Using {kaggle_dataset()} after handle lookup failed")
    return kaggle_dataset()


def fetch_existing_card_metadata(api: KaggleApi, handle: str) -> dict:
    """Pull title/subtitle/description so a version push does not wipe the card."""
    tmp_dir = tempfile.mkdtemp(prefix="kaggle_meta_")
    try:
        meta_path = api.dataset_metadata(handle, tmp_dir)
        return load_metadata_file(meta_path)
    except Exception as exc:  # noqa: BLE001 — card text is optional
        print(f"  Could not fetch existing Kaggle metadata ({exc})")
        return {}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def download_current_kaggle_data(api: KaggleApi) -> pd.DataFrame:
    """Download the latest Kaggle version and return all laps CSVs (new + legacy names)."""
    print("  Downloading current Kaggle dataset…")
    tmp_dir = tempfile.mkdtemp(prefix="kaggle_dl_")
    try:
        last_error: Exception | None = None
        downloaded = False
        for ref in dataset_handle_candidates():
            try:
                listing = api.dataset_list_files(ref)
                files = getattr(listing, "dataset_files", None) or getattr(listing, "files", None) or []
                if not files and isinstance(listing, dict):
                    files = listing.get("datasetFiles") or listing.get("files") or []
                names: list[str] = []
                for item in files:
                    name = getattr(item, "name", None) or (item.get("name") if isinstance(item, dict) else None)
                    if name:
                        names.append(name)
                if not names:
                    # Newer kaggle clients 404 on DownloadDataset; per-file download still works.
                    api.dataset_download_files(ref, path=tmp_dir, unzip=True)
                else:
                    for name in names:
                        if not is_kaggle_laps_csv(name):
                            continue
                        api.dataset_download_file(ref, name, path=tmp_dir, force=True, quiet=False)
                print(f"  Downloaded {ref}")
                downloaded = True
                break
            except Exception as exc:  # noqa: BLE001 — try legacy slug
                last_error = exc
                print(f"  Download failed for {ref} ({exc})")
        if not downloaded:
            if last_error is not None:
                raise last_error
            print("  No existing Kaggle CSV found — starting fresh.")
            return pd.DataFrame()

        all_dfs = []
        for fname in os.listdir(tmp_dir):
            decoded = fname.replace("%20", " ")
            if not (is_kaggle_laps_csv(fname) or is_kaggle_laps_csv(decoded)):
                continue
            fpath = os.path.join(tmp_dir, fname)
            df = pd.read_csv(fpath, low_memory=False)
            all_dfs.append(df)
            print(f"  Found: {decoded} ({len(df):,} rows)")

        if not all_dfs:
            print("  No existing laps CSV found — starting fresh.")
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
    """Fetch lap-level data from BigQuery, joining laps + sessions for circuit name."""
    print("  Querying BigQuery laps…")
    query = f"""
        SELECT
            l.season,
            s.event_name,
            COALESCE(s.circuit, s.event_name) AS circuit,
            s.session_type,
            l.driver_code                     AS driver,
            CAST(l.driver_number AS INT64)    AS driver_number,
            CAST(l.lap_number    AS INT64)    AS lap_number,
            l.lap_duration,
            l.compound,
            l.tyre_age_laps                   AS tyre_age,
            l.stint_number,
            l.session_key
        FROM `{PROJECT}.{DATASET}.laps` l
        JOIN (
            SELECT DISTINCT session_key, event_name, circuit, session_type
            FROM `{PROJECT}.{DATASET}.sessions`
        ) s ON l.session_key = s.session_key
        WHERE l.driver_code IS NOT NULL
          AND l.lap_number  IS NOT NULL
    """
    df = client.query(query).to_dataframe()
    print(f"  ✅  {len(df):,} laps fetched from BigQuery")
    return df


def fetch_ready_kaggle_laps(client: bigquery.Client) -> pd.DataFrame:
    """Rows already shaped for Kaggle (including telemetry JSON) in laps_kaggle."""
    print("  Querying laps_kaggle export table…")
    query = f"""
        SELECT
            season,
            event_name,
            circuit,
            session_type,
            driver,
            CAST(driver_number AS INT64) AS driver_number,
            CAST(lap_number    AS INT64) AS lap_number,
            lap_time,
            lap_duration,
            compound,
            tyre_age,
            stint_number,
            telemetry
        FROM `{PROJECT}.{DATASET}.laps_kaggle`
        WHERE driver IS NOT NULL
          AND lap_number IS NOT NULL
          AND telemetry IS NOT NULL
    """
    try:
        df = client.query(query).to_dataframe()
    except Exception as exc:  # noqa: BLE001 — table may be missing in some envs
        print(f"  laps_kaggle unavailable ({exc})")
        return pd.DataFrame()
    print(f"  ✅  {len(df):,} ready-made Kaggle rows from laps_kaggle")
    return df


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
    """Ensure the Kaggle API can authenticate (prefer KAGGLE_API_TOKEN)."""
    kdir = Path(os.path.expanduser("~/.kaggle"))
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if token:
        kdir.mkdir(parents=True, exist_ok=True)
        access = kdir / "access_token"
        if not access.is_file() or access.read_text().strip() != token:
            access.write_text(token)
            access.chmod(0o600)
        return
    if (kdir / "access_token").is_file() or (kdir / "kaggle.json").is_file():
        return
    user = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()
    if user and key:
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


def combine_kaggle_frames(existing_df: pd.DataFrame, new_rows: pd.DataFrame) -> pd.DataFrame:
    if existing_df.empty:
        combined = new_rows
    else:
        existing_trimmed = existing_df[new_rows.columns.intersection(existing_df.columns)]
        combined = pd.concat([existing_trimmed, new_rows], ignore_index=True)
    return combined.drop_duplicates(
        subset=["season", "event_name", "session_type", "driver_number", "lap_number"]
    ).sort_values(["season", "event_name", "session_type", "driver_number", "lap_number"])


# ── Step 6: Upload to Kaggle ──────────────────────────────────────────────────

def apply_kaggle_metadata(api: KaggleApi, handle: str, columns: list[str] | None = None) -> None:
    """Write dataset-metadata.json and PATCH license/tags/schema on the live listing."""
    require_existing_dataset_id()
    existing_card = fetch_existing_card_metadata(api, handle)
    last_error: Exception | None = None
    tmp_dir = tempfile.mkdtemp(prefix="kaggle_meta_")
    try:
        for license_name in kaggle_license_candidates():
            metadata = build_dataset_metadata(
                columns=columns,
                existing=existing_card,
                live_handle=handle,
            )
            metadata["licenses"] = [{"name": license_name}]
            write_metadata_file(os.path.join(tmp_dir, "dataset-metadata.json"), metadata)
            print(f"  Updating dataset settings (license={license_name}, tags, provenance)…")
            try:
                api.dataset_metadata_update(handle, tmp_dir)
                print(f"  ✅  Dataset settings updated with license {license_name}")
                return
            except SystemExit as exc:
                last_error = RuntimeError(f"Kaggle metadata update exited ({exc})")
                print(f"  License {license_name} rejected, trying next…")
            except Exception as exc:  # noqa: BLE001 — try next standard license
                last_error = exc
                print(f"  License {license_name} failed ({exc}), trying next…")
        if last_error is not None:
            raise last_error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def upload_to_kaggle(combined_df: pd.DataFrame, api: KaggleApi | None = None):
    """Save all_laps.csv and publish a version plus usability metadata."""
    require_existing_dataset_id()
    ensure_kaggle_auth()
    if api is None:
        api = KaggleApi()
        api.authenticate()

    today = datetime.now().strftime("%-d %B %Y")
    handle = resolve_dataset_handle(api)
    existing_card = fetch_existing_card_metadata(api, handle)
    metadata = build_dataset_metadata(
        columns=list(combined_df.columns),
        existing=existing_card,
        live_handle=handle,
    )

    tmp_dir = tempfile.mkdtemp(prefix="kaggle_upload_")
    try:
        out_path = os.path.join(tmp_dir, KAGGLE_CSV_NAME)
        combined_df.to_csv(out_path, index=False)
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        print(f"  Saved: {KAGGLE_CSV_NAME} ({size_mb:.1f} MB, {len(combined_df):,} rows)")

        write_metadata_file(os.path.join(tmp_dir, "dataset-metadata.json"), metadata)
        notes = f"Auto-update: {len(combined_df):,} laps as of {today}"
        print(f"  Uploading → kaggle.com/datasets/{metadata['id']} (handle {handle})…")
        api.dataset_create_version(tmp_dir, notes, quiet=False, convert_to_csv=False)

        print("  Updating dataset settings (license, tags, provenance)…")
        try:
            api.dataset_metadata_update(handle, tmp_dir)
        except SystemExit:
            # Current Kaggle client exit(1)s on a rejected license name.
            print("  Named license was rejected; retrying standard license names…")
            apply_kaggle_metadata(api, handle, columns=list(combined_df.columns))
        print(f"  ✅  Uploaded {KAGGLE_CSV_NAME} with usability metadata")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_kaggle_upload(*, republish: bool = False, metadata_only: bool = False) -> None:
    print("\n📤  F1 → Kaggle Upload")
    print(f"    BigQuery : {PROJECT}.{DATASET}")
    print(f"    Kaggle   : {kaggle_dataset()}")
    if kaggle_dataset() != KAGGLE_DATASET_LEGACY:
        print(f"    Legacy   : {KAGGLE_DATASET_LEGACY} (fallback until slug rename)\n")
    else:
        print()

    ensure_kaggle_auth()
    api = KaggleApi()
    api.authenticate()
    print("  ✅  Kaggle authenticated\n")

    if metadata_only:
        handle = resolve_dataset_handle(api)
        apply_kaggle_metadata(api, handle)
        print("\n✅  Kaggle metadata update complete.\n")
        return

    bq = bigquery.Client(project=PROJECT)

    print("── Step 1: Download existing Kaggle data…")
    existing_df = download_current_kaggle_data(api)

    print("\n── Step 2: Fetch laps from BigQuery…")
    ready_df = fetch_ready_kaggle_laps(bq)
    bq_laps = fetch_bq_laps(bq)
    if ready_df.empty and bq_laps.empty:
        print("  No laps in BigQuery. Nothing to upload.")
        return

    print("\n── Step 3: Identify new laps…")
    new_ready = find_new_laps(ready_df, existing_df) if not ready_df.empty else ready_df
    new_laps = find_new_laps(bq_laps, existing_df) if not bq_laps.empty else bq_laps
    if new_ready.empty and new_laps.empty and not republish:
        print("  Nothing new to upload. Kaggle dataset is already up to date.")
        return

    combined = existing_df
    if not new_ready.empty:
        print(f"  Appending {len(new_ready):,} ready-made export rows (incl. US GP FP3 when present).")
        combined = combine_kaggle_frames(combined, new_ready)
    if new_laps.empty and new_ready.empty:
        print("  Republish requested — re-uploading current laps with metadata.")
        if combined.empty:
            telemetry_df = fetch_telemetry_for_laps(bq, bq_laps)
            combined = build_kaggle_rows(bq_laps, telemetry_df)
    elif not new_laps.empty:
        print("\n── Step 4: Fetch telemetry for new laps…")
        telemetry_df = fetch_telemetry_for_laps(bq, new_laps)
        print("\n── Step 5: Build Kaggle rows…")
        new_kaggle_rows = build_kaggle_rows(new_laps, telemetry_df)
        print(f"  ✅  {len(new_kaggle_rows):,} rows built")
        combined = combine_kaggle_frames(combined, new_kaggle_rows)

    print(f"  ✅  Total rows for upload: {len(combined):,}")
    print("\n── Step 6: Upload to Kaggle…")
    upload_to_kaggle(combined, api=api)
    print("\n✅  Kaggle upload complete.\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Upload F1 laps to Kaggle")
    parser.add_argument(
        "--republish",
        action="store_true",
        help="Re-upload the current CSV with metadata even if no new laps exist",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="PATCH license/tags/schema on the live listing without uploading files",
    )
    args = parser.parse_args(argv)
    run_kaggle_upload(
        republish=args.republish or env_flag("KAGGLE_REPUBLISH"),
        metadata_only=args.metadata_only,
    )


if __name__ == "__main__":
    main()
