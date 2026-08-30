"""Cancel / SIGTERM must not resurrect a finished job."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import job_control  # noqa: E402


def test_status_guard_blocks_resurrection() -> None:
    assert "failed" in job_control.status_guard_sql("succeeded")
    assert "cancelled" in job_control.status_guard_sql("succeeded")
    assert "queued" in job_control.status_guard_sql("cancelled")
    assert job_control.status_guard_sql(None) == ""


def test_stop_signal_maps_cancelling_to_cancelled() -> None:
    assert job_control.desired_status_on_stop("cancelling") == "cancelled"
    assert job_control.desired_status_on_stop("running") == "failed"
    assert job_control.desired_status_on_stop("queued") == "failed"
    assert job_control.desired_status_on_stop("failed") is None
    assert job_control.desired_status_on_stop("cancelled") is None
    assert job_control.desired_status_on_stop("succeeded") is None


if __name__ == "__main__":
    test_status_guard_blocks_resurrection()
    test_stop_signal_maps_cancelling_to_cancelled()
    print("ok")
