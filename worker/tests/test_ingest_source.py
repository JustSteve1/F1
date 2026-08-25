"""INGEST_SOURCE must be fastf1 (or unset)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ingest_source  # noqa: E402


def test_unset_is_fastf1() -> None:
    os.environ.pop("INGEST_SOURCE", None)
    assert ingest_source.assert_fastf1_ingest() == "fastf1"


def test_fastf1_ok() -> None:
    os.environ["INGEST_SOURCE"] = "FastF1"
    assert ingest_source.assert_fastf1_ingest() == "fastf1"


def test_openf1_rejected() -> None:
    os.environ["INGEST_SOURCE"] = "openf1"
    try:
        ingest_source.assert_fastf1_ingest()
    except RuntimeError as exc:
        assert "FastF1 only" in str(exc)
        return
    raise AssertionError("expected RuntimeError")


if __name__ == "__main__":
    test_unset_is_fastf1()
    test_fastf1_ok()
    test_openf1_rejected()
    print("ok")
