"""Live telemetry merges car and position feeds onto a 0.5s grid."""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_telemetry  # noqa: E402
import timing_state  # noqa: E402


def _zipped(payload: dict) -> str:
    raw = json.dumps(payload).encode()
    return base64.b64encode(zlib.compress(raw)[2:-4]).decode()


def _state() -> dict:
    state = timing_state.new_state()
    timing_state.apply_message(
        state,
        "SessionInfo",
        {
            "Meeting": {
                "Name": "Singapore Grand Prix",
                "Location": "Marina Bay",
                "Circuit": {"ShortName": "Singapore"},
            },
            "Name": "Race",
            "Type": "Race",
            "Path": "2026/2026-10-11_Singapore_Grand_Prix/2026-10-11_Race/",
            "StartDate": "2026-10-11T12:00:00",
        },
    )
    return state


def _car(when: datetime, speed: int, rpm: int) -> str:
    return _zipped(
        {
            "Entries": [
                {
                    "Utc": when.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "Cars": {
                        "1": {
                            "Channels": {
                                "0": rpm,
                                "2": speed,
                                "3": 1,
                                "4": 0,
                                "5": 0,
                                "45": 0,
                            }
                        }
                    },
                }
            ]
        }
    )


def _pos(when: datetime, x: int, y: int, z: int) -> str:
    return _zipped(
        {
            "Position": [
                {
                    "Timestamp": when.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "Entries": {"1": {"X": x, "Y": y, "Z": z, "Status": "OnTrack"}},
                }
            ]
        }
    )


class LiveTelemetryTests(unittest.TestCase):
    def test_half_second_sample_has_the_export_channels(self) -> None:
        start = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
        log = live_telemetry.TelemetryLog(Path("/tmp"), bigquery=False)
        state = _state()
        first = log.observe(state, "CarData.z", _car(start, 8, 3823))
        self.assertEqual(first, [])
        rows = log.observe(state, "Position.z", _pos(start, -12617, -10683, 0))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lap_number"], 1)
        self.assertEqual(row["lap_time_sec"], 0.0)
        self.assertEqual(row["interval_sec"], 0.5)
        self.assertEqual(row["speed"], 8)
        self.assertEqual(row["throttle"], 0)
        self.assertFalse(row["brake"])
        self.assertEqual(row["gear"], 1)
        self.assertEqual(row["rpm"], 3823)
        self.assertEqual(row["drs"], 0)
        self.assertEqual(row["x"], -1261.7)
        self.assertEqual(row["y"], -1068.3)
        self.assertEqual(row["z"], 0)
        self.assertEqual(row["session_type"], "R")
        self.assertEqual(row["circuit"], "Marina Bay")
        later = log.observe(
            state, "CarData.z", _car(start + timedelta(milliseconds=200), 20, 4000)
        )
        self.assertEqual(later, [])
        half = log.observe(
            state,
            "Position.z",
            _pos(start + timedelta(milliseconds=500), -12000, -10000, 10),
        )
        self.assertEqual([item["lap_time_sec"] for item in half], [0.5])
        self.assertEqual(half[0]["x"], -1200.0)

    def test_a_new_lap_restarts_the_clock(self) -> None:
        start = datetime(2026, 10, 11, 12, 5, tzinfo=timezone.utc)
        log = live_telemetry.TelemetryLog(Path("/tmp"), bigquery=False)
        state = _state()
        log.observe(state, "CarData.z", _car(start, 80, 9000))
        log.observe(state, "Position.z", _pos(start, 100, 200, 30))
        timing_state.apply_message(
            state,
            "TimingData",
            {"Lines": {"1": {"NumberOfLaps": 1, "LastLapTime": {"Value": "1:40.000"}}}},
        )
        nxt = start + timedelta(seconds=90)
        rows = log.observe(state, "Position.z", _pos(nxt, 110, 210, 30))
        self.assertEqual(rows[0]["lap_number"], 2)
        self.assertEqual(rows[0]["lap_time_sec"], 0.0)

    def test_stored_points_and_full_laps_are_not_queued_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = live_telemetry.TelemetryLog(Path(tmp), bigquery=False)
            existing = {
                "session_key": 7,
                "driver_number": "44",
                "lap_number": 10,
                "lap_time_sec": 1.5,
            }
            fresh = {
                "session_key": 7,
                "driver_number": "44",
                "lap_number": 10,
                "lap_time_sec": 2.0,
            }
            blocked = {
                "session_key": 7,
                "driver_number": "44",
                "lap_number": 11,
                "lap_time_sec": 0.0,
            }
            log.remember_points({log._point_id(existing)})
            log.remember_laps({log._lap_key(blocked)})
            log._queue([existing, fresh, blocked])
            self.assertEqual([row["lap_time_sec"] for row in log._pending], [2.0])
            self.assertEqual(log.skipped, 2)


if __name__ == "__main__":
    unittest.main()
