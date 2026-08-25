"""v1 ingest is FastF1 only. OpenF1 is not a fallback."""

from __future__ import annotations

import os

ALLOWED = "fastf1"


def ingest_source() -> str:
    return (os.environ.get("INGEST_SOURCE") or ALLOWED).strip().lower() or ALLOWED


def assert_fastf1_ingest() -> str:
    source = ingest_source()
    if source != ALLOWED:
        raise RuntimeError(
            f"INGEST_SOURCE={source!r} is not supported. "
            "v1 ingest is FastF1 only (OpenF1 is not a fallback)."
        )
    return source
