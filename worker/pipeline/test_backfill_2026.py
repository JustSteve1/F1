"""Ordering and skip rules for the 2026 backfill. No network."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backfill_2026 as backfill  # noqa: E402


class OrderTests(unittest.TestCase):
    def test_recent_weekends_come_first(self) -> None:
        ordered = backfill.order_events(
            [
                "Bahrain Grand Prix",
                "Mexico City Grand Prix",
                "Las Vegas Grand Prix",
                "Australian Grand Prix",
            ]
        )
        self.assertEqual(
            ordered,
            [
                "Las Vegas Grand Prix",
                "Mexico City Grand Prix",
                "Bahrain Grand Prix",
                "Australian Grand Prix",
            ],
        )


class SkipTests(unittest.TestCase):
    def test_sessions_with_laps_are_not_imported_again(self) -> None:
        missing = backfill.sessions_to_import(["FP1", "SQ", "Q", "R"], {"SQ", "Q"})
        self.assertEqual(missing, ["FP1", "R"])

    def test_a_race_that_has_not_started_is_left_out(self) -> None:
        now = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
        codes = backfill.due_session_codes(
            [
                {"code": "R", "dateUtc": "2026-11-22T04:00:00+00:00"},
                {"code": "FP1", "dateUtc": "2026-11-27T13:30:00+00:00"},
            ],
            now,
        )
        self.assertEqual(codes, ["R"])


if __name__ == "__main__":
    unittest.main()
