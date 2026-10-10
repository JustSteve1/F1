"""Static-archive telemetry is one sample every 0.5s, in metres, pedals 0-100."""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import archive_telemetry  # noqa: E402


def _deflate_line(offset: str, payload: dict) -> str:
    compressor = zlib.compressobj(wbits=-15)
    raw = compressor.compress(json.dumps(payload).encode()) + compressor.flush()
    return f"{offset}\"{base64.b64encode(raw).decode()}\n"


class ArchiveTelemetryTests(unittest.TestCase):
    def test_half_second_samples_match_kaggle_channels(self) -> None:
        # Archive offset 0 is 09:36:20. Lap 1 finishes at 100s (09:38:00).
        # Lap 2 finishes 2.0s later. Throttle 104 is a full pedal.
        # Position coordinates are tenths of a metre.
        stamps = (
            "2026-10-10T09:38:00.000000Z",
            "2026-10-10T09:38:00.500000Z",
            "2026-10-10T09:38:01.000000Z",
            "2026-10-10T09:38:01.500000Z",
            "2026-10-10T09:38:02.000000Z",
        )
        car = {
            "Entries": [
                {
                    "Utc": stamp,
                    "Cars": {
                        "1": {
                            "Channels": {
                                "0": 11194 if index == 0 else 11412,
                                "2": 294 if index == 0 else 297,
                                "3": 7,
                                "4": 104 if index == 0 else 100,
                                "5": 0 if index == 0 else 104,
                            }
                        }
                    },
                }
                for index, stamp in enumerate(stamps)
            ]
        }
        position = {
            "Position": [
                {
                    "Timestamp": stamp,
                    "Entries": {
                        "1": {
                            "X": -11357 if index == 0 else -13892,
                            "Y": -13897 if index == 0 else -11485,
                            "Z": 852 if index == 0 else 835,
                        }
                    },
                }
                for index, stamp in enumerate(stamps)
            ]
        }
        timing = (
            '00:01:40.000{"Lines":{"1":{"NumberOfLaps":1}}}\n'
            '00:01:42.000{"Lines":{"1":{"NumberOfLaps":2,"LastLapTime":{"Value":"0:02.000"}}}}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchor = {
                "Entries": [
                    {
                        "Utc": "2026-10-10T09:36:20.000000Z",
                        "Cars": {"1": {"Channels": {"0": 0, "2": 0, "3": 0, "4": 0, "5": 0}}},
                    }
                ]
            }
            (root / "CarData.z.jsonStream").write_text(
                _deflate_line("00:00:00.000", anchor) + _deflate_line("00:01:40.000", car),
                encoding="utf-8",
            )
            (root / "Position.z.jsonStream").write_text(
                _deflate_line("00:01:40.000", position),
                encoding="utf-8",
            )
            (root / "TimingData.jsonStream").write_text(timing, encoding="utf-8")
            rows = archive_telemetry.build_telemetry(
                root,
                session_key=2837898403,
                season=2026,
                event_name="Singapore Grand Prix",
                session_type="S",
                circuit="Marina Bay",
            )

        lap2 = [row for row in rows if row["lap_number"] == 2]
        self.assertEqual([row["lap_time_sec"] for row in lap2], [0.0, 0.5, 1.0, 1.5, 2.0])
        first = lap2[0]
        self.assertEqual(first["throttle"], 100)
        self.assertIs(first["brake"], False)
        self.assertEqual(first["drs"], 0)
        self.assertEqual(first["gear"], 7)
        self.assertEqual(first["rpm"], 11194)
        self.assertEqual(first["speed"], 294)
        self.assertAlmostEqual(first["x"], -1135.7)
        self.assertAlmostEqual(first["y"], -1389.7)
        self.assertAlmostEqual(first["z"], 85.2)
        self.assertIs(lap2[1]["brake"], True)
        self.assertEqual(lap2[1]["throttle"], 100)
        self.assertEqual(first["session_key"], 2837898403)
        self.assertEqual(
            datetime.fromisoformat(first["date"]),
            datetime(2026, 10, 10, 9, 38, tzinfo=timezone.utc),
        )
        self.assertTrue(all(row["lap_number"] == 2 for row in rows))


if __name__ == "__main__":
    unittest.main()
