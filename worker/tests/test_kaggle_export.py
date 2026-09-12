"""Kaggle export table is 13 columns, 2 Hz telemetry JSON, no BQ JSON type."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from google.cloud.bigquery import SchemaField

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import kaggle_export as kexp  # noqa: E402


def _session(laps: pd.DataFrame, event_name="Italian Grand Prix", location="Monza"):
    return SimpleNamespace(
        event={"EventName": event_name, "Location": location},
        laps=laps,
    )


def test_schema_has_no_json_fields() -> None:
    assert kexp.KAGGLE_EXPORT_COLUMNS == [
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
    assert [f.name for f in kexp.KAGGLE_EXPORT_SCHEMA] == kexp.KAGGLE_EXPORT_COLUMNS
    assert all(f.field_type.upper() != "JSON" for f in kexp.KAGGLE_EXPORT_SCHEMA)
    tel = next(f for f in kexp.KAGGLE_EXPORT_SCHEMA if f.name == "telemetry")
    assert tel.field_type.upper() == "STRING"


def test_kaggle_interval_is_2hz() -> None:
    assert kexp.TELEMETRY_INTERVAL_KAGGLE == 0.5
    assert kexp._is_kaggle_tick(0.0)
    assert kexp._is_kaggle_tick(0.5)
    assert kexp._is_kaggle_tick(1.0)
    assert not kexp._is_kaggle_tick(0.1)
    assert not kexp._is_kaggle_tick(0.2)


def test_build_frame_packs_2hz_json() -> None:
    laps = pd.DataFrame(
        [
            {
                "DriverNumber": "1",
                "Driver": "VER",
                "LapNumber": 12,
                "LapTime": timedelta(seconds=81.234),
                "Compound": "MEDIUM",
                "TyreLife": 4,
                "Stint": 2,
            }
        ]
    )
    telemetry = pd.DataFrame(
        [
            {
                "season": 2026,
                "event_name": "Italian Grand Prix",
                "session_type": "R",
                "driver_number": "1",
                "lap_number": 12,
                "lap_time_sec": t,
                "speed": 280 + i,
                "throttle": 100,
                "brake": False,
                "gear": 8,
                "rpm": 11000,
                "drs": 0,
                "x": 100.0 + i,
                "y": 50.0,
                "z": 1.0,
            }
            for i, t in enumerate((0.0, 0.1, 0.2, 0.5))
        ]
    )
    loaded = {(2026, "R"): _session(laps)}
    out = kexp.build_kaggle_export_frame(loaded, telemetry)
    assert list(out.columns) == kexp.KAGGLE_EXPORT_COLUMNS
    assert len(out) == 1
    row = out.iloc[0]
    assert row["driver"] == "VER"
    assert int(row["driver_number"]) == 1
    assert row["lap_time"] == "1:21.234"
    assert abs(float(row["lap_duration"]) - 81.234) < 1e-6
    assert row["compound"] == "MEDIUM"
    blob = json.loads(row["telemetry"])
    times = [p["t"] for p in blob]
    assert times == [0.0, 0.5]
    assert 0.1 not in times and 0.2 not in times


def test_merge_replaces_overlapping_keys() -> None:
    existing = pd.DataFrame(
        [
            {
                "season": 2026,
                "event_name": "Australian Grand Prix",
                "circuit": "Melbourne",
                "session_type": "R",
                "driver": "NOR",
                "driver_number": 4,
                "lap_number": 1,
                "lap_time": "1:20.000",
                "lap_duration": 80.0,
                "compound": "SOFT",
                "tyre_age": 1,
                "stint_number": 1,
                "telemetry": "[]",
            },
            {
                "season": 2026,
                "event_name": "Italian Grand Prix",
                "circuit": "Monza",
                "session_type": "R",
                "driver": "VER",
                "driver_number": 1,
                "lap_number": 12,
                "lap_time": "1:22.000",
                "lap_duration": 82.0,
                "compound": "HARD",
                "tyre_age": 8,
                "stint_number": 3,
                "telemetry": '[{"t":0.0}]',
            },
        ]
    )
    export = pd.DataFrame(
        [
            {
                "season": 2026,
                "event_name": "Italian Grand Prix",
                "circuit": "Monza",
                "session_type": "R",
                "driver": "VER",
                "driver_number": 1,
                "lap_number": 12,
                "lap_time": "1:21.234",
                "lap_duration": 81.234,
                "compound": "MEDIUM",
                "tyre_age": 4,
                "stint_number": 2,
                "telemetry": '[{"t":0.0},{"t":0.1}]',
            }
        ]
    )
    merged = kexp.merge_kaggle_csv(existing, export)
    assert len(merged) == 2
    ita = merged[
        (merged["event_name"] == "Italian Grand Prix") & (merged["lap_number"] == 12)
    ].iloc[0]
    assert ita["lap_time"] == "1:21.234"
    assert "0.1" in str(ita["telemetry"])
    aus = merged[merged["event_name"] == "Australian Grand Prix"]
    assert len(aus) == 1


def test_ensure_table_rejects_json_telemetry() -> None:
    table = SimpleNamespace(
        schema=[
            SchemaField("season", "INT64"),
            SchemaField("telemetry", "JSON"),
        ]
    )
    client = SimpleNamespace(get_table=lambda _ref: table)
    try:
        kexp.ensure_kaggle_export_table(client)
    except RuntimeError as exc:
        assert "JSON" in str(exc)
        assert "Recreate" in str(exc)
        return
    raise AssertionError("expected RuntimeError")


def test_check_existing_keys_export_table() -> None:
    class _Job:
        def to_dataframe(self):
            return pd.DataFrame(
                [{"season": 2026, "session_type": "FP1"}]
            )

    calls: list[str] = []

    class _Client:
        def query(self, sql, job_config=None):
            calls.append(sql)
            return _Job()

    existing = kexp.check_existing_kaggle_export(
        _Client(), [2026], "Spanish Grand Prix", ["FP1"]
    )
    assert existing == {(2026, "FP1"): True}
    assert "for_kaggle_export" in calls[0]


if __name__ == "__main__":
    test_schema_has_no_json_fields()
    test_kaggle_interval_is_2hz()
    test_build_frame_packs_2hz_json()
    test_merge_replaces_overlapping_keys()
    test_ensure_table_rejects_json_telemetry()
    test_check_existing_keys_export_table()
    print("ok")
