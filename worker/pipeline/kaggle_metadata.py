"""
Kaggle dataset identity and usability metadata.

Slug convention: formula-one-<topic> (matches formula-one-2026-china-gp-energy-management).
File convention: stable all_laps.csv so file/column descriptions survive each version.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

KAGGLE_CSV_NAME = "all_laps.csv"
KAGGLE_DATASET_DEFAULT = "stevefza/formula-one-all-laps-telemetry"
KAGGLE_DATASET_LEGACY = "stevefza/f1-2026-bahrain-testing-day-2"
KAGGLE_DATASET_ID_DEFAULT = 9485317
# Locked to the existing public listing so votes/downloads cannot move to a new slug.
KAGGLE_DATASET_ID_LOCKED = 9485317
KAGGLE_LICENSE_DEFAULT = "CC-BY-4.0"
# Newer Kaggle Settings API rejects some documented slugs. Try these in order.
KAGGLE_LICENSE_CANDIDATES = (
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC0-1.0",
    "CC-BY-SA-3.0",
    "ODbL-1.0",
)
KAGGLE_KEYWORDS_DEFAULT = (
    "sports",
    "time series analysis",
    "tabular",
    "beginner",
)
KAGGLE_TITLE_DEFAULT = "Formula One (F1) - All Laps & Telemetry Dataset"
KAGGLE_SUBTITLE_DEFAULT = (
    "ML-ready lap level dataset - All drivers, cars, tracks & telemetry (2026)"
)
KAGGLE_UPDATE_FREQUENCY = "weekly"
KAGGLE_FILE_DESCRIPTION = (
    "One row per lap across the live Formula One dataset. "
    "The telemetry column is a JSON array of 2 Hz samples "
    "(speed, throttle, brake, gear, rpm, drs, x, y, z)."
)
KAGGLE_PROVENANCE = (
    "Lap and telemetry data from FastF1 / official timing feeds and OpenF1, "
    "cleaned in the Interval.ai BigQuery pipeline (f1-data-library). "
    "Telemetry is downsampled to 0.5 second / 2 Hz for export. "
    "This is not an official Formula 1 product."
)
COLUMN_FIELDS: list[dict[str, str]] = [
    {"name": "season", "description": "Championship year", "type": "integer"},
    {"name": "event_name", "description": "Official or pipeline event name", "type": "string"},
    {"name": "circuit", "description": "Circuit name", "type": "string"},
    {
        "name": "session_type",
        "description": "FP1, FP2, FP3, Q, SQ, Sprint, R, or testing day",
        "type": "string",
    },
    {"name": "driver", "description": "Driver code (VER, HAM, …)", "type": "string"},
    {"name": "driver_number", "description": "Race number", "type": "integer"},
    {"name": "lap_number", "description": "Lap index in that session", "type": "integer"},
    {
        "name": "lap_time",
        "description": "Formatted M:SS.mmm; 0:00.000 means no valid time",
        "type": "string",
    },
    {"name": "lap_duration", "description": "Lap time in seconds", "type": "numeric"},
    {"name": "compound", "description": "Tyre compound", "type": "string"},
    {"name": "tyre_age", "description": "Laps on this tyre set", "type": "integer"},
    {"name": "stint_number", "description": "Stint index", "type": "integer"},
    {
        "name": "telemetry",
        "description": "JSON array of 0.5 s / 2 Hz samples for the lap",
        "type": "string",
    },
]
_COLUMN_FIELD_BY_NAME = {field["name"]: field for field in COLUMN_FIELDS}


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def kaggle_dataset() -> str:
    return os.environ.get("KAGGLE_DATASET", KAGGLE_DATASET_DEFAULT).strip() or KAGGLE_DATASET_DEFAULT


def kaggle_dataset_id() -> int | None:
    raw = os.environ.get("KAGGLE_DATASET_ID", str(KAGGLE_DATASET_ID_DEFAULT)).strip()
    if raw.lower() in {"", "0", "none", "null"}:
        return None
    return int(raw)


def require_existing_dataset_id() -> int:
    """Refuse any upload that is not the existing public listing."""
    dataset_id = kaggle_dataset_id()
    if dataset_id != KAGGLE_DATASET_ID_LOCKED:
        raise RuntimeError(
            "Refusing Kaggle upload: this pipeline is locked to dataset id "
            f"{KAGGLE_DATASET_ID_LOCKED} ({KAGGLE_DATASET_LEGACY}) so votes "
            "and downloads stay on the existing listing. "
            f"Got KAGGLE_DATASET_ID={dataset_id!r}."
        )
    return dataset_id


def kaggle_license() -> str:
    return os.environ.get("KAGGLE_LICENSE", KAGGLE_LICENSE_DEFAULT).strip() or KAGGLE_LICENSE_DEFAULT


def kaggle_license_candidates() -> list[str]:
    preferred = kaggle_license()
    seen: list[str] = []
    for name in (preferred, *KAGGLE_LICENSE_CANDIDATES):
        if name and name not in seen:
            seen.append(name)
    return seen


def kaggle_keywords() -> list[str]:
    raw = os.environ.get("KAGGLE_KEYWORDS", "").strip()
    if not raw:
        return list(KAGGLE_KEYWORDS_DEFAULT)
    return [part.strip() for part in raw.split(",") if part.strip()]


def dataset_handle_candidates() -> list[str]:
    """New slug first, then the live Bahrain-testing slug until Kaggle Settings is renamed."""
    seen: list[str] = []
    for ref in (kaggle_dataset(), KAGGLE_DATASET_LEGACY):
        if ref and ref not in seen:
            seen.append(ref)
    return seen


def is_kaggle_laps_csv(filename: str) -> bool:
    name = Path(filename).name
    if not name.lower().endswith(".csv"):
        return False
    if name == KAGGLE_CSV_NAME:
        return True
    return "all laps" in name.lower()


def schema_fields_for_columns(columns: Iterable[str]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for column in columns:
        known = _COLUMN_FIELD_BY_NAME.get(column)
        if known:
            fields.append(dict(known))
        else:
            fields.append(
                {
                    "name": column,
                    "description": column.replace("_", " "),
                    "type": "string",
                }
            )
    return fields


def build_dataset_metadata(
    *,
    columns: Iterable[str] | None = None,
    existing: dict[str, Any] | None = None,
    live_handle: str | None = None,
) -> dict[str, Any]:
    existing = existing or {}
    fields = schema_fields_for_columns(columns if columns is not None else [f["name"] for f in COLUMN_FIELDS])
    subtitle = (existing.get("subtitle") or KAGGLE_SUBTITLE_DEFAULT).strip()
    if not (20 <= len(subtitle) <= 80):
        subtitle = KAGGLE_SUBTITLE_DEFAULT
    # Version `id` must be the live listing. A new slug here without id_no
    # would create a second dataset and zero the stats.
    metadata: dict[str, Any] = {
        "id": live_handle or KAGGLE_DATASET_LEGACY,
        "id_no": require_existing_dataset_id(),
        "title": (existing.get("title") or KAGGLE_TITLE_DEFAULT).strip() or KAGGLE_TITLE_DEFAULT,
        "subtitle": subtitle,
        "licenses": [{"name": kaggle_license()}],
        "keywords": kaggle_keywords(),
        "expectedUpdateFrequency": KAGGLE_UPDATE_FREQUENCY,
        "userSpecifiedSources": KAGGLE_PROVENANCE,
        "resources": [
            {
                "path": KAGGLE_CSV_NAME,
                "description": KAGGLE_FILE_DESCRIPTION,
                "schema": {"fields": fields},
            }
        ],
        "data": [
            {
                "name": KAGGLE_CSV_NAME,
                "description": KAGGLE_FILE_DESCRIPTION,
                "columns": fields,
            }
        ],
    }
    description = existing.get("description")
    if isinstance(description, str) and description.strip():
        metadata["description"] = description
    return metadata


def write_metadata_file(path: str | Path, metadata: dict[str, Any], *, for_update: bool = False) -> Path:
    """Write dataset-metadata.json as a JSON object.

    Current KaggleApi.dataset_metadata_update json.load()s the file once and
    expects a dict. Older clients double-decoded a JSON string; load_metadata_file
    still accepts that form.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    return dest


def load_metadata_file(path: str | Path) -> dict[str, Any]:
    raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected metadata object in {path}")
    return raw
