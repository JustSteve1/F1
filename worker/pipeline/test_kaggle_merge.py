"""The Kaggle file keeps orphan rows and lets the view replace a live lap."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kaggle_merge  # noqa: E402


def _row(**overrides):
    row = {column: None for column in kaggle_merge.KAGGLE_COLUMNS}
    row.update(
        {
            "season": 2026,
            "event_name": "Singapore Grand Prix",
            "circuit": "Singapore",
            "session_type": "S",
            "driver": "VER",
            "driver_number": 1,
            "lap_number": 5,
            "lap_time": "2:40.924",
            "lap_duration": 160.924,
            "compound": "INTERMEDIATE",
            "tyre_age": 4,
            "stint_number": 4,
            "telemetry": "[]",
        }
    )
    row.update(overrides)
    return row


class KaggleMergeTests(unittest.TestCase):
    def test_view_row_replaces_the_same_lap_and_keeps_kaggle_only_rows(self) -> None:
        published = _row(telemetry="[]", lap_time="2:40.924")
        older = _row(lap_number=3, driver="LEC", driver_number=16, lap_time="1:35.000")
        batch = _row(telemetry='[{"t":0.0,"speed":280}]', lap_time="2:40.100", lap_duration=160.1)
        combined = kaggle_merge.combine_kaggle_rows([published, older], [batch])
        by_lap = {row["lap_number"]: row for row in combined}
        self.assertEqual(len(combined), 2)
        self.assertEqual(by_lap[5]["telemetry"], '[{"t":0.0,"speed":280}]')
        self.assertEqual(by_lap[5]["lap_time"], "2:40.100")
        self.assertEqual(by_lap[3]["driver"], "LEC")
        self.assertFalse(kaggle_merge.rows_unchanged([published, older], combined))

    def test_identical_view_does_not_count_as_a_change(self) -> None:
        existing = [_row()]
        combined = kaggle_merge.combine_kaggle_rows(existing, [_row(driver_number=1.0)])
        self.assertTrue(kaggle_merge.rows_unchanged(existing, combined))


if __name__ == "__main__":
    unittest.main()
