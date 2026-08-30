"""Step caps must fit inside Cloud Run --task-timeout=14400."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import job_runner  # noqa: E402


def test_step_timeouts_fit_cloud_run() -> None:
    total = sum(job_runner.STEP_TIMEOUTS_SEC.values())
    assert job_runner.STEP_TIMEOUTS_SEC["resample_telemetry"] >= 90 * 60
    assert job_runner.STEP_TIMEOUTS_SEC["upload_telemetry"] >= 45 * 60
    assert total <= 4 * 60 * 60


if __name__ == "__main__":
    test_step_timeouts_fit_cloud_run()
    print("ok")
