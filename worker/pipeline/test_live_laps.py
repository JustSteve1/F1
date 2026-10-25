"""Local lap log keeps the newest completed lap first and drops duplicates."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_laps  # noqa: E402
import timing_state  # noqa: E402


def _row(lap_number: int) -> dict:
    row = {column: None for column in timing_state.LAP_COLUMNS}
    row.update(
        {
            "session_key": 1,
            "meeting_key": 1,
            "driver_number": "1",
            "lap_number": lap_number,
            "lap_duration": 90.0 + lap_number,
            "imported_at": f"2026-10-10T12:00:{lap_number:02d}Z",
        }
    )
    return row


class LapLogTests(unittest.TestCase):
    def test_newest_lap_is_first_and_a_repeat_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = live_laps.LapLog(Path(tmp), bigquery=False)
            self.assertEqual(log.add([_row(1)]), 1)
            self.assertEqual(log.add([_row(2), _row(1)]), 1)
            stored = json.loads((Path(tmp) / "live-laps.json").read_text())
            self.assertEqual([row["lap_number"] for row in stored["laps"]], [2, 1])

            reopened = live_laps.LapLog(Path(tmp), bigquery=False)
            self.assertEqual(reopened.add([_row(2)]), 0)


if __name__ == "__main__":
    unittest.main()