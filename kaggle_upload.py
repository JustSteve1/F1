"""
BigQuery → Kaggle export for stevefza/f1-2026-bahrain-testing-day-2

Default deploy is incremental: download the live Kaggle CSV, export only new
laps from BigQuery, append them, and publish a new dataset version.

Usage:
    python kaggle_upload.py deploy
    python kaggle_upload.py export --out exports/kaggle
    python kaggle_upload.py upload --dir exports/kaggle
    python kaggle_upload.py --print-sql
    python kaggle_upload.py deploy --full-refresh

Auth:
    BigQuery : GOOGLE_APPLICATION_CREDENTIALS=/path/to/cursorf1.json
               or gcloud auth application-default login
                  --impersonate-service-account=cursorf1@f1-data-library.iam.gserviceaccount.com
    Kaggle   : KAGGLE_API_TOKEN (preferred) OR ~/.kaggle/kaggle.json

Consumers:
    import kagglehub
    path = kagglehub.dataset_download("stevefza/f1-2026-bahrain-testing-day-2")
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    def load_dotenv(*_args, **_kwargs):
        return False

ROOT = Path(__file__).resolve().parent
SQL_PATH = ROOT / "sql" / "kaggle_laps_export.sql"
KEYS_SQL_PATH = ROOT / "sql" / "kaggle_lap_keys.sql"
METADATA_PATH = ROOT / "kaggle" / "dataset-metadata.json"

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
KAGGLE_DATASET = os.environ.get("KAGGLE_DATASET", "stevefza/f1-2026-bahrain-testing-day-2")

KAGGLE_COLUMNS = [
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
TELEMETRY_KEYS = ["t", "speed", "throttle", "brake", "gear", "rpm", "drs", "x", "y", "z"]
LAP_TIME_RE = re.compile(r"^\d+:\d{2}\.\d{3}$")
DEDUP_COLS = ["season", "event_name", "session_type", "driver_number", "lap_number"]
MAX_NEW_LAP_STRUCTS = 4000


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _common_predicates(
    *,
    season: int | None,
    event: str | None,
    session_type: str | None,
) -> dict[str, str]:
    return {
        "season": f"season = {int(season)}" if season is not None else "TRUE",
        "event": f"event_name = {_sql_string(event)}" if event else "TRUE",
        "session": f"session_type = {_sql_string(session_type)}" if session_type else "TRUE",
    }


def _fill_sql(template: str, *, project: str, dataset: str, preds: dict[str, str], new_laps: str = "TRUE") -> str:
    return (
        template.replace("{{PROJECT}}", project)
        .replace("{{DATASET}}", dataset)
        .replace("{{SEASON_PREDICATE}}", preds["season"])
        .replace("{{EVENT_PREDICATE}}", preds["event"])
        .replace("{{SESSION_PREDICATE}}", preds["session"])
        .replace("{{NEW_LAPS_PREDICATE}}", new_laps)
    )


def render_export_sql(
    *,
    project: str | None = None,
    dataset: str | None = None,
    season: int | None = 2026,
    event: str | None = None,
    session_type: str | None = None,
    new_laps_pred: str = "TRUE",
    sql_path: Path | None = None,
) -> str:
    """Render the agreed BigQuery export with optional filters."""
    project = project or PROJECT
    dataset = dataset or DATASET
    sql_path = sql_path or SQL_PATH
    preds = _common_predicates(season=season, event=event, session_type=session_type)
    return _fill_sql(
        sql_path.read_text(),
        project=project,
        dataset=dataset,
        preds=preds,
        new_laps=new_laps_pred,
    )


def render_keys_sql(
    *,
    project: str | None = None,
    dataset: str | None = None,
    season: int | None = 2026,
    event: str | None = None,
    session_type: str | None = None,
    sql_path: Path | None = None,
) -> str:
    """Render the cheap lap-identity query used for incremental diffs."""
    project = project or PROJECT
    dataset = dataset or DATASET
    sql_path = sql_path or KEYS_SQL_PATH
    preds = _common_predicates(season=season, event=event, session_type=session_type)
    return _fill_sql(sql_path.read_text(), project=project, dataset=dataset, preds=preds)


def new_laps_predicate(keys_df, *, max_structs: int = MAX_NEW_LAP_STRUCTS) -> str:
    """BigQuery predicate that keeps only the given session_key/driver/lap rows."""
    if keys_df is None or len(keys_df) == 0:
        return "FALSE"
    if len(keys_df) > max_structs:
        session_keys = sorted({int(k) for k in keys_df["session_key"].dropna()})
        if not session_keys:
            return "FALSE"
        return f"session_key IN ({', '.join(str(k) for k in session_keys)})"
    parts = []
    for _, row in keys_df.iterrows():
        parts.append(
            "STRUCT<session_key INT64, driver_number INT64, lap_number INT64>"
            f"({int(row['session_key'])}, {int(row['driver_number'])}, {int(row['lap_number'])})"
        )
    return (
        "(session_key, CAST(driver_number AS INT64), CAST(lap_number AS INT64)) "
        f"IN UNNEST([{', '.join(parts)}])"
    )


def _normalize_key_frame(df):
    import pandas as pd

    out = df.copy()
    for col in ("season", "driver_number", "lap_number"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    for col in ("event_name", "session_type"):
        if col in out.columns:
            out[col] = out[col].astype(str)
    return out


def find_new_lap_keys(bq_keys_df, existing_df):
    """Return BQ key rows that are not already on Kaggle."""
    import pandas as pd

    if bq_keys_df is None or bq_keys_df.empty:
        return bq_keys_df if bq_keys_df is not None else pd.DataFrame()
    if existing_df is None or existing_df.empty:
        return bq_keys_df
    left = _normalize_key_frame(bq_keys_df)
    right = _normalize_key_frame(existing_df)
    missing = [c for c in DEDUP_COLS if c not in right.columns]
    if missing:
        return bq_keys_df
    merged = left.merge(right[DEDUP_COLS].drop_duplicates(), on=DEDUP_COLS, how="left", indicator=True)
    return merged.loc[merged["_merge"] == "left_only"].drop(columns=["_merge"])


def append_new_laps(existing_df, new_df):
    """Keep every existing Kaggle row and add only unseen laps."""
    import pandas as pd

    if existing_df is None or existing_df.empty:
        return new_df
    if new_df is None or new_df.empty:
        return existing_df.loc[:, [c for c in KAGGLE_COLUMNS if c in existing_df.columns]]
    existing = existing_df.copy()
    for col in KAGGLE_COLUMNS:
        if col not in existing.columns:
            existing[col] = None
    existing = existing.loc[:, KAGGLE_COLUMNS]
    new = new_df.loc[:, KAGGLE_COLUMNS]
    combined = pd.concat([existing, new], ignore_index=True)
    return combined.drop_duplicates(subset=DEDUP_COLS, keep="first")


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return value != value  # NaN
    except Exception:
        return False


def validate_schema(df, *, require_rows: bool = True) -> None:
    """Raise ValueError if the frame does not match the agreed Kaggle schema."""
    cols = list(df.columns)
    if cols != KAGGLE_COLUMNS:
        raise ValueError(
            f"Export columns do not match agreed schema.\n"
            f"  expected: {KAGGLE_COLUMNS}\n"
            f"  got:      {cols}"
        )
    if require_rows and len(df) == 0:
        raise ValueError("Export produced 0 rows")

    bad_times = []
    bad_tel = []
    for i, (lap_time, tel) in enumerate(zip(df["lap_time"], df["telemetry"])):
        if not _is_missing(lap_time) and not LAP_TIME_RE.match(str(lap_time)):
            bad_times.append((i, lap_time))
        if _is_missing(tel):
            bad_tel.append((i, "missing"))
            continue
        try:
            parsed = json.loads(tel) if isinstance(tel, str) else tel
        except json.JSONDecodeError as exc:
            bad_tel.append((i, f"invalid json: {exc}"))
            continue
        if not isinstance(parsed, list):
            bad_tel.append((i, f"expected array, got {type(parsed).__name__}"))
            continue
        if parsed:
            extra = set(parsed[0].keys()) - set(TELEMETRY_KEYS)
            missing = set(TELEMETRY_KEYS) - set(parsed[0].keys())
            if extra or missing:
                bad_tel.append((i, f"telemetry keys extra={sorted(extra)} missing={sorted(missing)}"))
        if len(bad_times) >= 5 and len(bad_tel) >= 5:
            break

    if bad_times:
        raise ValueError(f"lap_time is not M:SS.mmm: {bad_times[:5]}")
    if bad_tel:
        raise ValueError(f"telemetry JSON is not the agreed 0.5s struct: {bad_tel[:5]}")


def load_metadata() -> dict:
    return json.loads(METADATA_PATH.read_text())


def export_filename(when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"All Laps - {when.strftime('%-d %B %Y')}.csv"


def write_bundle(df, out_dir: Path, *, filename: str | None = None) -> Path:
    """Write CSV + dataset-metadata.json for `kaggle datasets version`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = filename or export_filename()
    csv_path = out_dir / filename

    ordered = df.loc[:, KAGGLE_COLUMNS].copy()
    ordered.to_csv(csv_path, index=False)

    meta = load_metadata()
    meta["id"] = KAGGLE_DATASET
    if meta.get("resources"):
        meta["resources"][0]["path"] = filename
    (out_dir / "dataset-metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    return csv_path


def fetch_export(sql: str):
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT)
    print(f"  Querying {PROJECT}.{DATASET}…")
    df = client.query(sql).to_dataframe()
    print(f"  ✅  {len(df):,} laps exported")
    return df


def fetch_bq_keys(*, season: int | None, event: str | None, session_type: str | None):
    sql = render_keys_sql(season=season, event=event, session_type=session_type)
    print("  Querying BigQuery lap keys…")
    return fetch_export(sql)


def download_current_kaggle_csv(dest_dir: Path):
    """Download the live dataset CSV(s). Prefers kagglehub."""
    import pandas as pd

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        import kagglehub

        path = Path(kagglehub.dataset_download(KAGGLE_DATASET))
        print(f"  kagglehub download: {path}")
        search_root = path
    except Exception as exc:
        print(f"  kagglehub download failed ({exc}); trying Kaggle CLI…")
        cmd = kaggle_cli_cmd(
            "datasets",
            "download",
            "-d",
            KAGGLE_DATASET,
            "-p",
            str(dest_dir),
            "--unzip",
        )
        subprocess.run(cmd, check=True)
        search_root = dest_dir

    frames = []
    for csv in Path(search_root).rglob("*.csv"):
        if "All Laps" not in csv.name:
            continue
        print(f"  Found: {csv.name}")
        frames.append(pd.read_csv(csv, low_memory=False))
    if not frames:
        return pd.DataFrame(columns=KAGGLE_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.loc[:, [c for c in KAGGLE_COLUMNS if c in combined.columns]]
    return combined.drop_duplicates(subset=[c for c in DEDUP_COLS if c in combined.columns])


def ensure_kaggle_auth() -> str:
    """
    Make sure the official Kaggle CLI or kagglehub can authenticate.

    Returns the uploader that is ready: 'cli' or 'kagglehub'.
    """
    user = os.environ.get("KAGGLE_USERNAME", "").strip()
    key = os.environ.get("KAGGLE_KEY", "").strip()
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    cfg = Path.home() / ".kaggle" / "kaggle.json"
    token_file = Path.home() / ".kaggle" / "access_token"

    if user and key:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        if not cfg.is_file():
            cfg.write_text(json.dumps({"username": user, "key": key}))
            cfg.chmod(0o600)
        return "cli"
    if cfg.is_file():
        return "cli"
    if token or token_file.is_file():
        return "kagglehub"
    raise RuntimeError(
        "Kaggle credentials not found.\n"
        "  Preferred: set KAGGLE_API_TOKEN\n"
        "  Official CLI: copy kaggle.json to ~/.kaggle/kaggle.json\n"
        "    or set KAGGLE_USERNAME + KAGGLE_KEY\n"
        "  Create keys at https://www.kaggle.com/settings/api"
    )


def kaggle_cli_cmd(*args: str) -> list[str]:
    found = shutil.which("kaggle")
    if found:
        return [found, *args]
    return [sys.executable, "-m", "kaggle", *args]


def upload_via_cli(folder: Path, notes: str) -> None:
    cmd = kaggle_cli_cmd(
        "datasets", "version", "-p", str(folder), "-m", notes, "--dir-mode", "zip"
    )
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def upload_via_kagglehub(folder: Path, notes: str) -> None:
    import kagglehub

    print(f"  kagglehub.dataset_upload({KAGGLE_DATASET!r}, {str(folder)!r})")
    kagglehub.dataset_upload(KAGGLE_DATASET, str(folder), version_notes=notes)


def resolve_uploader(requested: str) -> str:
    ready = ensure_kaggle_auth()
    if requested == "auto":
        return ready
    if requested == "cli" and ready != "cli":
        print("  Official CLI credentials missing; falling back to kagglehub")
        return "kagglehub"
    if requested == "kagglehub":
        return "kagglehub"
    return requested


def cmd_export(args) -> Path | None:
    full_refresh = bool(getattr(args, "full_refresh", False))
    existing = None

    if full_refresh:
        print("── Full refresh from BigQuery (not incremental)…")
        sql = render_export_sql(
            season=args.season,
            event=args.event,
            session_type=args.session_type,
            new_laps_pred="TRUE",
        )
        df = fetch_export(sql)
        validate_schema(df)
    else:
        print("── Incremental append…")
        tmp = Path(tempfile.mkdtemp(prefix="kaggle_dl_"))
        try:
            existing = download_current_kaggle_csv(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print(f"  existing Kaggle rows: {len(existing):,}")

        bq_keys = fetch_bq_keys(
            season=args.season,
            event=args.event,
            session_type=args.session_type,
        )
        new_keys = find_new_lap_keys(bq_keys, existing)
        already = 0 if bq_keys is None else len(bq_keys) - len(new_keys)
        print(f"  {len(new_keys):,} new laps / {already:,} already on Kaggle")
        if new_keys is None or new_keys.empty:
            print("  Nothing new to export. Kaggle dataset is already up to date.")
            return None

        pred = new_laps_predicate(new_keys)
        sql = render_export_sql(
            season=args.season,
            event=args.event,
            session_type=args.session_type,
            new_laps_pred=pred,
        )
        new_df = fetch_export(sql)
        validate_schema(new_df)
        df = append_new_laps(existing, new_df)
        print(f"  combined rows: {len(df):,}")

    out_dir = Path(args.out)
    csv_path = write_bundle(df, out_dir)
    size_mb = csv_path.stat().st_size / 1024 / 1024
    print(f"  Wrote {csv_path.name} ({size_mb:.1f} MB, {len(df):,} rows)")
    print(f"  Metadata: {out_dir / 'dataset-metadata.json'}")
    return out_dir


def cmd_upload(args) -> None:
    folder = Path(args.dir)
    meta = folder / "dataset-metadata.json"
    if not meta.is_file():
        raise FileNotFoundError(f"Missing {meta} — run export first")
    csvs = list(folder.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No CSV in {folder} — run export first")

    notes = args.version_notes or f"Auto-update: {csvs[0].name}"
    print(f"  Uploading → kaggle.com/datasets/{KAGGLE_DATASET}")
    if args.dry_run:
        print(f"  dry-run: would upload {folder} ({notes})")
        return
    uploader = resolve_uploader(args.uploader)
    if uploader == "cli":
        upload_via_cli(folder, notes)
    else:
        upload_via_kagglehub(folder, notes)
    print("  Dataset version uploaded")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Incrementally append new F1 laps from BigQuery onto the live Kaggle dataset"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="deploy",
        choices=["export", "upload", "deploy"],
        help="export = BigQuery only, upload = CLI only, deploy = both (default)",
    )
    parser.add_argument("--season", type=int, default=2026, help="Season year (default: 2026)")
    parser.add_argument("--all-seasons", action="store_true", help="Do not filter by season")
    parser.add_argument("--event", type=str, default=None, help="Optional event_name filter")
    parser.add_argument("--session-type", type=str, default=None, help="Optional session_type filter")
    parser.add_argument("--out", type=str, default="exports/kaggle", help="Export folder")
    parser.add_argument(
        "--dir",
        type=str,
        default=None,
        help="Existing folder with CSV + dataset-metadata.json (upload)",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Rebuild the file from BigQuery only (skip download/diff/append)",
    )
    parser.add_argument(
        "--uploader",
        choices=["cli", "kagglehub", "auto"],
        default="auto",
        help="auto uses kagglehub when KAGGLE_API_TOKEN is set (default)",
    )
    parser.add_argument("--version-notes", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Export (if needed) but do not upload")
    parser.add_argument("--print-sql", action="store_true", help="Print the rendered BigQuery export and exit")
    return parser


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.all_seasons:
        args.season = None
    if args.dir is None:
        args.dir = args.out
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    global PROJECT, DATASET, KAGGLE_DATASET
    PROJECT = os.environ.get("BQ_PROJECT", PROJECT)
    DATASET = os.environ.get("BQ_DATASET", DATASET)
    KAGGLE_DATASET = os.environ.get("KAGGLE_DATASET", KAGGLE_DATASET)

    parser = build_parser()
    args = normalize_args(parser.parse_args(argv))
    command = args.command or "deploy"

    if getattr(args, "print_sql", False):
        print(
            render_export_sql(
                season=getattr(args, "season", 2026),
                event=getattr(args, "event", None),
                session_type=getattr(args, "session_type", None),
            )
        )
        return 0

    print("\nF1 → Kaggle")
    print(f"    BigQuery : {PROJECT}.{DATASET}")
    print(f"    Kaggle   : {KAGGLE_DATASET}")
    print(f"    Command  : {command}")
    print(f"    Mode     : {'full-refresh' if args.full_refresh else 'incremental append'}\n")

    try:
        if command == "export":
            cmd_export(args)
        elif command == "upload":
            cmd_upload(args)
        else:
            out = cmd_export(args)
            if out is None:
                print("\nDone. No upload needed.\n")
                return 0
            args.dir = str(out)
            cmd_upload(args)
    except Exception as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1

    print("\nDone.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
