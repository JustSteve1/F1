"""Laps dataframe must match the extended BQ schema; JSON cols cannot use Parquet."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
from google.cloud.bigquery import SchemaField

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import f1_telemetry_import as pipe  # noqa: E402


def _field(name: str, field_type: str) -> SchemaField:
    return SchemaField(name, field_type)


def _client(fields: list[tuple[str, str]]) -> MagicMock:
    table = SimpleNamespace(schema=[_field(n, t) for n, t in fields])
    client = MagicMock()
    client.get_table.return_value = table
    return client


def test_schema_for_load_drops_json() -> None:
    schema = [
        _field("lap_number", "INT64"),
        _field("segments_sector_1", "JSON"),
        _field("i1_speed", "FLOAT"),
    ]
    kept = pipe.schema_for_load(schema)
    assert [f.name for f in kept] == ["lap_number", "i1_speed"]


def test_format_lap_time() -> None:
    assert pipe.format_lap_time(72.345) == "1:12.345"
    assert pipe.format_lap_time(None) is None


def test_lap_row_populates_openf1_aliases() -> None:
    lap = pd.Series(
        {
            "DriverNumber": "1",
            "Driver": "VER",
            "Team": "Red Bull",
            "Position": 1,
            "LapNumber": 4,
            "LapTime": timedelta(seconds=72.345),
            "Time": timedelta(seconds=200.0),
            "Sector1Time": timedelta(seconds=20.1),
            "Sector2Time": timedelta(seconds=25.2),
            "Sector3Time": timedelta(seconds=27.045),
            "PitOutTime": timedelta(seconds=1.0),
            "SpeedI1": 280.0,
            "SpeedI2": 290.0,
            "SpeedST": 310.0,
            "Compound": "SOFT",
            "TyreLife": 2,
            "Stint": 1,
            "FreshTyre": True,
            "IsAccurate": True,
            "IsPersonalBest": False,
            "Deleted": False,
            "DeletedReason": None,
            "FastF1Generated": False,
            "TrackStatus": "1",
            "LapStartDate": pd.Timestamp("2026-09-06T13:00:00Z"),
            "Sector1Segments": [2048, 2049],
        }
    )
    row = pipe.lap_row_from_fastf1(
        lap,
        session_key=42,
        year=2026,
        event_name="Italian Grand Prix",
        session_type="R",
        imported_at="2026-09-10T00:00:00+00:00",
    )
    assert row["sector_1_time"] == row["duration_sector_1"] == 20.1
    assert row["speed_i1"] == row["i1_speed"] == 280.0
    assert row["speed_st"] == row["st_speed"] == 310.0
    assert row["is_pit_out_lap"] is True
    assert row["date_start"] == row["lap_start_date"]
    assert row["lap_time_formatted"] == "1:12.345"
    assert row["segments_sector_1"] == [2048, 2049]
    assert row["segments_sector_2"] is None


def test_coerce_fills_missing_columns_including_json() -> None:
    client = _client(
        [
            ("lap_number", "INT64"),
            ("duration_sector_1", "FLOAT"),
            ("segments_sector_1", "JSON"),
            ("i1_speed", "FLOAT"),
        ]
    )
    df = pd.DataFrame(
        {"lap_number": [1], "i1_speed": [280.0], "segments_sector_1": [[2048, 2049]]}
    )
    out = pipe._coerce_df_for_table(client, "proj.ds.laps", df)
    assert list(out.columns) == [
        "lap_number",
        "duration_sector_1",
        "segments_sector_1",
        "i1_speed",
    ]
    assert out.loc[0, "segments_sector_1"] == [2048, 2049]
    assert pd.isna(out.loc[0, "duration_sector_1"])


def test_json_tables_load_via_ndjson() -> None:
    client = _client(
        [
            ("lap_number", "INT64"),
            ("segments_sector_1", "JSON"),
        ]
    )
    load_job = MagicMock()
    load_job.job_id = "job-ndjson"
    client.load_table_from_file.return_value = load_job

    logs: list[str] = []
    result = pipe.load_dataframe(
        client,
        "proj.ds.laps",
        pd.DataFrame({"lap_number": [1], "segments_sector_1": [[2048, 2049]]}),
        log=logs.append,
        job_id="abc",
        label="laps",
    )

    assert result["method"] == "ndjson"
    client.load_table_from_dataframe.assert_not_called()
    cfg = client.load_table_from_file.call_args.kwargs["job_config"]
    assert [f.name for f in cfg.schema] == ["lap_number", "segments_sector_1"]
    buf = client.load_table_from_file.call_args.args[0]
    buf.seek(0)
    row = json.loads(buf.read().decode("utf-8"))
    assert row["lap_number"] == 1
    assert row["segments_sector_1"] == [2048, 2049]
    assert any("ndjson" in m for m in logs)


def test_parquet_fallback_strips_json_from_job_schema() -> None:
    """BQ Parquet loads reject any destination schema that includes JSON."""
    client = _client(
        [
            ("lap_number", "INT64"),
            ("segments_sector_1", "JSON"),
            ("duration_sector_1", "FLOAT"),
        ]
    )
    client.load_table_from_file.side_effect = RuntimeError("ndjson failed")
    client.load_table_from_dataframe.side_effect = RuntimeError("schema mismatch")
    parquet_job = MagicMock()
    parquet_job.job_id = "job-pq"
    client.load_table_from_uri.return_value = parquet_job

    class _Blob:
        def upload_from_filename(self, _path: str) -> None:
            return None

    class _Bucket:
        def blob(self, _name: str) -> _Blob:
            return _Blob()

    class _Storage:
        def bucket(self, _name: str) -> _Bucket:
            return _Bucket()

    fake_storage = MagicMock()
    fake_storage.Client.return_value = _Storage()
    sys.modules["google.cloud.storage"] = fake_storage

    result = pipe.load_dataframe(
        client,
        "proj.ds.laps",
        pd.DataFrame({"lap_number": [1]}),
        log=lambda _m: None,
        job_id="abc",
        label="laps",
    )

    assert result["method"] == "parquet"
    cfg = client.load_table_from_uri.call_args.kwargs["job_config"]
    assert [f.name for f in cfg.schema] == ["lap_number", "duration_sector_1"]
    assert all(f.field_type.upper() != "JSON" for f in cfg.schema)


def test_non_json_tables_still_use_dataframe() -> None:
    client = _client([("lap_number", "INT64"), ("i1_speed", "FLOAT")])
    load_job = MagicMock()
    load_job.job_id = "job-df"
    client.load_table_from_dataframe.return_value = load_job

    result = pipe.load_dataframe(
        client,
        "proj.ds.laps",
        pd.DataFrame({"lap_number": [1], "i1_speed": [280.0]}),
        log=lambda _m: None,
        job_id="abc",
        label="laps",
    )

    assert result["method"] == "dataframe"
    client.load_table_from_file.assert_not_called()
    cfg = client.load_table_from_dataframe.call_args.kwargs["job_config"]
    assert [f.name for f in cfg.schema] == ["lap_number", "i1_speed"]


if __name__ == "__main__":
    test_schema_for_load_drops_json()
    test_format_lap_time()
    test_lap_row_populates_openf1_aliases()
    test_coerce_fills_missing_columns_including_json()
    test_json_tables_load_via_ndjson()
    test_parquet_fallback_strips_json_from_job_schema()
    test_non_json_tables_still_use_dataframe()
    print("ok")
