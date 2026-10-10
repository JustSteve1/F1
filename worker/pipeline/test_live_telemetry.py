"""Live car packets become a 10 Hz lap, and the subscriber listens for them."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_subscriber  # noqa: E402
import live_telemetry  # noqa: E402


class LiveTelemetryTests(unittest.TestCase):
    def test_subscriber_listens_for_car_and_position(self) -> None:
        self.assertIn("CarData.z", live_subscriber.SUBSCRIBE_TOPICS)
        self.assertIn("Position.z", live_subscriber.SUBSCRIBE_TOPICS)
        items = live_subscriber.iter_feed_items(
            ["CarData.z", {"Entries": []}, "2026-10-11T12:00:00Z"]
        )
        self.assertEqual(items[0][0], "CarData.z")

    def test_finished_lap_is_ten_hertz(self) -> None:
        start = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
        buffer = live_telemetry.CarBuffer()
        # Native feed is slower than 10 Hz. The grid still lands every 0.1s.
        for step in range(8):
            instant = start + timedelta(seconds=step * 0.16)
            stamp = instant.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            buffer.add(
                "CarData.z",
                {
                    "Entries": [
                        {
                            "Utc": stamp,
                            "Cars": {
                                "1": {
                                    "Channels": {
                                        "0": 11825,
                                        "2": 225,
                                        "3": 5,
                                        "4": 104,
                                        "5": 0,
                                    }
                                }
                            },
                        }
                    ]
                },
            )
            buffer.add(
                "Position.z",
                {
                    "Position": [
                        {
                            "Timestamp": stamp,
                            "Entries": {"1": {"X": 1136, "Y": -967, "Z": 188}},
                        }
                    ]
                },
            )

        points = buffer.resample("1", start + timedelta(seconds=1.0), 1.0)
        times = [point["lap_time_sec"] for point in points]
        self.assertEqual(times, [round(step * 0.1, 1) for step in range(11)])
        self.assertEqual(points[0]["interval_sec"], 0.1)
        self.assertEqual(points[0]["throttle"], 100)
        self.assertIs(points[0]["brake"], False)
        self.assertEqual(points[0]["gear"], 5)
        self.assertEqual(points[0]["rpm"], 11825)
        self.assertEqual(points[0]["speed"], 225)
        self.assertAlmostEqual(points[0]["x"], 113.6)
        self.assertAlmostEqual(points[0]["y"], -96.7)
        self.assertAlmostEqual(points[0]["z"], 18.8)

        log = live_telemetry.LiveTelemetryLog(bigquery=False)
        lap = {
            "session_key": 7,
            "meeting_key": 7,
            "season": 2026,
            "event_name": "Singapore Grand Prix",
            "session_type": "R",
            "driver_number": "1",
            "lap_number": 10,
            "lap_duration": 1.0,
        }
        written = log.record([lap], buffer, start + timedelta(seconds=1.0))
        self.assertEqual(written, 11)
        self.assertEqual(log.record([lap], buffer, start + timedelta(seconds=1.0)), 0)


if __name__ == "__main__":
    unittest.main()
