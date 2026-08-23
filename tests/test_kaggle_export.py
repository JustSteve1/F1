import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import kaggle_upload as kag


AGREED_COLUMNS = [
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

TELEMETRY_SAMPLE = json.dumps(
    [
        {
            "t": 0.0,
            "speed": 80,
            "throttle": 40,
            "brake": 0,
            "gear": 2,
            "rpm": 9000,
            "drs": 0,
            "x": 100.1,
            "y": 200.2,
            "z": 3.3,
        }
    ],
    separators=(",", ":"),
)


def sample_row(**overrides):
    row = {
        "season": 2026,
        "event_name": "Bahrain Grand Prix",
        "circuit": "Sakhir",
        "session_type": "R",
        "driver": "LEC",
        "driver_number": 16,
        "lap_number": 1,
        "lap_time": "1:34.273",
        "lap_duration": 94.273,
        "compound": "SOFT",
        "tyre_age": 2,
        "stint_number": 1,
        "telemetry": TELEMETRY_SAMPLE,
    }
    row.update(overrides)
    return row


def test_sql_file_selects_agreed_aliases():
    sql = kag.SQL_PATH.read_text()
    for alias in (
        "AS driver",
        "AS driver_number",
        "AS lap_time",
        "AS tyre_age",
        "AS telemetry",
    ):
        assert alias in sql
    for col in ("season", "event_name", "circuit", "session_type", "lap_number", "lap_duration", "compound", "stint_number"):
        assert col in sql


def test_sql_downsamples_to_half_second():
    sql = kag.SQL_PATH.read_text()
    assert "MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0" in sql
    assert "TO_JSON_STRING(ta.telemetry)" in sql
    assert "driver_number_mapping" in sql
    assert "{{NEW_LAPS_PREDICATE}}" in sql


def test_keys_sql_is_cheap_identity_query():
    sql = kag.render_keys_sql()
    assert "{{" not in sql
    assert "ARRAY_AGG" not in sql
    assert "TO_JSON_STRING" not in sql
    assert "session_key" in sql
    assert "season = 2026" in sql
    assert "MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0" in sql


def test_render_sql_default_season_and_filters():
    sql = kag.render_export_sql()
    assert "{{" not in sql
    assert "`f1-data-library.f1_data_library_DS.telemetry`" in sql
    assert "season = 2026" in sql
    assert "event_name =" not in sql
    sql_event = kag.render_export_sql(event="Bahrain Grand Prix", session_type="R")
    assert "event_name = 'Bahrain Grand Prix'" in sql_event
    assert "session_type = 'R'" in sql_event
    sql_all = kag.render_export_sql(season=None)
    assert "season = 2026" not in sql_all


def test_render_sql_escapes_quotes():
    sql = kag.render_export_sql(event="Driver's Parade")
    assert "event_name = 'Driver''s Parade'" in sql


def test_metadata_targets_live_dataset():
    meta = kag.load_metadata()
    assert meta["id"] == "stevefza/f1-2026-bahrain-testing-day-2"
    assert meta["id_no"] == 9485317
    field_names = [f["name"] for f in meta["resources"][0]["schema"]["fields"]]
    assert field_names == AGREED_COLUMNS


def test_validate_schema_accepts_agreed_frame():
    df = pd.DataFrame([sample_row()])
    kag.validate_schema(df)


def test_validate_schema_rejects_wrong_columns():
    df = pd.DataFrame([sample_row()]).drop(columns=["telemetry"])
    with pytest.raises(ValueError, match="agreed schema"):
        kag.validate_schema(df)


def test_validate_schema_rejects_bad_lap_time_and_telemetry():
    df = pd.DataFrame([sample_row(lap_time="94.273")])
    with pytest.raises(ValueError, match="lap_time"):
        kag.validate_schema(df)
    df = pd.DataFrame([sample_row(telemetry='{"t":0}')])
    with pytest.raises(ValueError, match="telemetry"):
        kag.validate_schema(df)


def test_write_bundle_writes_cli_folder(tmp_path):
    df = pd.DataFrame([sample_row()])
    csv_path = kag.write_bundle(df, tmp_path, filename="All Laps - 22 August 2026.csv")
    assert csv_path.exists()
    written = pd.read_csv(csv_path)
    assert list(written.columns) == AGREED_COLUMNS
    meta = json.loads((tmp_path / "dataset-metadata.json").read_text())
    assert meta["id"] == kag.KAGGLE_DATASET
    assert meta["resources"][0]["path"] == "All Laps - 22 August 2026.csv"


def test_append_new_laps_keeps_existing_and_adds_unseen():
    existing = pd.DataFrame([sample_row(lap_number=1, driver="SAI")])
    new = pd.DataFrame([sample_row(lap_number=1, driver="LEC"), sample_row(lap_number=2)])
    merged = kag.append_new_laps(existing, new)
    assert len(merged) == 2
    row = merged.loc[merged["lap_number"] == 1].iloc[0]
    assert row["driver"] == "SAI"
    assert 2 in set(merged["lap_number"])


def test_export_filename_matches_live_dataset():
    name = kag.export_filename(__import__("datetime").datetime(2026, 8, 9))
    assert name == "All Laps - 9 August 2026.csv"


def test_parser_help_mentions_incremental_default():
    help_text = kag.build_parser().format_help()
    assert "full-refresh" in help_text
    assert "stevefza" in kag.KAGGLE_DATASET


def test_parser_defaults_to_deploy():
    args = kag.normalize_args(kag.build_parser().parse_args([]))
    assert args.command == "deploy"
    assert args.season == 2026
    assert args.uploader == "auto"
    assert args.full_refresh is False
    args = kag.normalize_args(kag.build_parser().parse_args(["--all-seasons", "--print-sql"]))
    assert args.season is None
    assert args.print_sql is True


def test_print_sql_exits_zero(capsys):
    rc = kag.main(["--print-sql", "--event", "Chinese Grand Prix"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "event_name = 'Chinese Grand Prix'" in out
    assert "TO_JSON_STRING(ta.telemetry)" in out


def test_kaggle_cli_cmd_uses_module_fallback(monkeypatch):
    monkeypatch.setattr(kag.shutil, "which", lambda _name: None)
    cmd = kag.kaggle_cli_cmd("datasets", "version", "-p", "/tmp")
    assert cmd[:3] == [sys.executable, "-m", "kaggle"]


def test_upload_dry_run(tmp_path, capsys):
    df = pd.DataFrame([sample_row()])
    kag.write_bundle(df, tmp_path, filename="All Laps - 22 August 2026.csv")
    rc = kag.main(["upload", "--dir", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert "dry-run" in capsys.readouterr().out


def _key_row(session_key, lap_number, **overrides):
    row = {
        "session_key": session_key,
        "season": 2026,
        "event_name": "Bahrain Grand Prix",
        "session_type": "R",
        "driver_number": 16,
        "lap_number": lap_number,
    }
    row.update(overrides)
    return row


def test_find_new_lap_keys_returns_only_unseen():
    bq = pd.DataFrame([_key_row(1, 1), _key_row(1, 2)])
    existing = pd.DataFrame([sample_row(lap_number=1)])
    new = kag.find_new_lap_keys(bq, existing)
    assert list(new["lap_number"]) == [2]


def test_find_new_lap_keys_all_new_when_kaggle_empty():
    bq = pd.DataFrame([_key_row(1, 1)])
    new = kag.find_new_lap_keys(bq, pd.DataFrame())
    assert len(new) == 1


def test_new_laps_predicate_unnest_and_empty():
    assert kag.new_laps_predicate(pd.DataFrame()) == "FALSE"
    keys = pd.DataFrame([_key_row(99, 3)])
    pred = kag.new_laps_predicate(keys)
    assert "UNNEST" in pred
    assert "99" in pred
    assert "3" in pred
    sql = kag.render_export_sql(new_laps_pred=pred)
    assert "{{" not in sql
    assert pred in sql


def test_new_laps_predicate_falls_back_to_session_keys():
    keys = pd.DataFrame([_key_row(i, 1) for i in range(5)])
    pred = kag.new_laps_predicate(keys, max_structs=2)
    assert pred.startswith("session_key IN (")
    assert "UNNEST" not in pred


def test_incremental_export_appends_only_new(monkeypatch, tmp_path):
    existing = pd.DataFrame([sample_row(lap_number=1, driver="SAI")])
    bq_keys = pd.DataFrame([_key_row(1, 1), _key_row(1, 2)])
    new_export = pd.DataFrame([sample_row(lap_number=2)])
    downloaded = {"n": 0}

    monkeypatch.setattr(kag, "download_current_kaggle_csv", lambda dest: downloaded.__setitem__("n", 1) or existing)
    monkeypatch.setattr(kag, "fetch_bq_keys", lambda **kwargs: bq_keys)
    monkeypatch.setattr(kag, "fetch_export", lambda sql: new_export)

    args = kag.normalize_args(kag.build_parser().parse_args(["export", "--out", str(tmp_path)]))
    out = kag.cmd_export(args)
    assert out == tmp_path
    assert downloaded["n"] == 1
    written = pd.read_csv(next(tmp_path.glob("All Laps*.csv")))
    assert len(written) == 2
    assert set(written["lap_number"]) == {1, 2}
    assert written.loc[written["lap_number"] == 1, "driver"].iloc[0] == "SAI"


def test_incremental_export_noop_when_no_new(monkeypatch, tmp_path):
    existing = pd.DataFrame([sample_row(lap_number=1)])
    bq_keys = pd.DataFrame([_key_row(1, 1)])
    monkeypatch.setattr(kag, "download_current_kaggle_csv", lambda dest: existing)
    monkeypatch.setattr(kag, "fetch_bq_keys", lambda **kwargs: bq_keys)

    def fail_export(_sql):
        raise AssertionError("full telemetry export should not run when there are no new laps")

    monkeypatch.setattr(kag, "fetch_export", fail_export)
    args = kag.normalize_args(kag.build_parser().parse_args(["export", "--out", str(tmp_path)]))
    assert kag.cmd_export(args) is None
    assert list(tmp_path.glob("*.csv")) == []


def test_full_refresh_skips_download_and_diff(monkeypatch, tmp_path):
    calls = {"download": 0, "keys": 0}

    def fail_download(_dest):
        calls["download"] += 1
        raise AssertionError("full-refresh should not download the live Kaggle CSV")

    def fail_keys(**_kwargs):
        calls["keys"] += 1
        raise AssertionError("full-refresh should not query lap keys")

    monkeypatch.setattr(kag, "download_current_kaggle_csv", fail_download)
    monkeypatch.setattr(kag, "fetch_bq_keys", fail_keys)
    monkeypatch.setattr(kag, "fetch_export", lambda sql: pd.DataFrame([sample_row()]))

    args = kag.normalize_args(
        kag.build_parser().parse_args(["export", "--full-refresh", "--out", str(tmp_path)])
    )
    out = kag.cmd_export(args)
    assert out == tmp_path
    assert calls["download"] == 0
    assert calls["keys"] == 0
    assert next(tmp_path.glob("All Laps*.csv")).exists()


def test_deploy_skips_upload_when_up_to_date(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(kag, "cmd_export", lambda _args: None)
    uploaded = {"n": 0}
    monkeypatch.setattr(kag, "cmd_upload", lambda _args: uploaded.__setitem__("n", uploaded["n"] + 1))
    rc = kag.main(["deploy", "--out", str(tmp_path)])
    assert rc == 0
    assert uploaded["n"] == 0
    assert "No upload needed" in capsys.readouterr().out
