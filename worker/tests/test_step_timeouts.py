"""Step caps must fit inside Cloud Run --task-timeout=14400 per active path."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import job_runner  # noqa: E402

LIMIT = 4 * 60 * 60


def _budget(params: dict) -> int:
    return sum(
        job_runner.STEP_TIMEOUTS_SEC[s]
        for s in job_runner._active_steps(params)
        if s in job_runner.STEP_TIMEOUTS_SEC
    )


def test_warehouse_path_timeouts_fit_cloud_run() -> None:
    total = _budget({"includeKaggle": False})
    assert job_runner.STEP_TIMEOUTS_SEC["resample_telemetry"] >= 90 * 60
    assert job_runner.STEP_TIMEOUTS_SEC["upload_telemetry"] >= 45 * 60
    assert total <= LIMIT


def test_kaggle_path_timeouts_fit_cloud_run() -> None:
    steps = job_runner._active_steps({"includeKaggle": True})
    assert "upload_kaggle_export" in steps
    assert "kaggle_upload" in steps
    assert "upload_sessions_laps" not in steps
    assert "laps_unified" not in steps
    assert job_runner.STEP_TIMEOUTS_SEC["kaggle_upload"] >= 40 * 60
    assert _budget({"includeKaggle": True}) <= LIMIT


if __name__ == "__main__":
    test_warehouse_path_timeouts_fit_cloud_run()
    test_kaggle_path_timeouts_fit_cloud_run()
    print("ok")
