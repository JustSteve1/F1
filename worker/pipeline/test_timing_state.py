"""Fixture test: a later TimingData patch must not wipe earlier lap fields."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import timing_state  # noqa: E402


class TimingStateTests(unittest.TestCase):
    def test_sector_update_keeps_last_lap_and_position(self) -> None:
        state = timing_state.new_state()
        timing_state.apply_message(
            state,
            "TimingData",
            {
                "Lines": {
                    "1": {
                        "Position": "3",
                        "LastLapTime": {"Value": "1:32.100", "PersonalFastest": False},
                    }
                }
            },
        )
        timing_state.apply_message(
            state,
            "DriverList",
            {"1": {"Tla": "VER", "RacingNumber": "1"}},
        )
        timing_state.apply_message(
            state,
            "TimingData",
            {"Lines": {"1": {"Sectors": {"0": {"Value": "28.1"}}}}},
        )
        timing_state.apply_message(
            state,
            "ExtrapolatedClock",
            {"Utc": "2026-10-04T09:00:00Z", "Remaining": "01:00:00"},
        )
        timing_state.apply_message(
            state,
            "SessionInfo",
            {"Name": "Race", "Type": "Race", "Meeting": {"Name": "Bahrain Grand Prix"}},
        )

        snap = timing_state.snapshot(state)
        row = snap["drivers"][0]
        self.assertEqual(row["driver_number"], "1")
        self.assertEqual(row["tla"], "VER")
        self.assertEqual(row["position"], "3")
        self.assertEqual(row["last_lap"], "1:32.100")
        self.assertEqual(row["sector1"], "28.1")
        self.assertIsNone(row["sector2"])
        self.assertEqual(snap["session"]["name"], "Race")
        self.assertEqual(snap["clock"]["Remaining"], "01:00:00")

    def test_segment_patch_keeps_sector_time(self) -> None:
        state = timing_state.new_state()
        timing_state.apply_message(
            state,
            "TimingData",
            {
                "Lines": {
                    "1": {
                        "Sectors": [
                            {"Value": "28.1"},
                            {"Value": "39.4"},
                            {"Value": "24.6"},
                        ]
                    }
                }
            },
        )
        timing_state.apply_message(
            state,
            "TimingData",
            {"Lines": {"1": {"Sectors": {"0": {"Segments": {"1": {"Status": 2048}}}}}}},
        )
        row = timing_state.snapshot(state)["drivers"][0]
        self.assertEqual(row["sector1"], "28.1")
        self.assertEqual(row["sector2"], "39.4")
        self.assertEqual(row["sector3"], "24.6")

    def test_replay_jsonl_matches_live_merge(self) -> None:
        messages = [
            (
                "TimingData",
                {"Lines": {"44": {"Position": "1", "LastLapTime": {"Value": "1:31.500"}}}},
            ),
            (
                "TimingData",
                {"Lines": {"44": {"Sectors": {"1": {"Value": "39.2"}}}}},
            ),
        ]
        state = timing_state.new_state()
        for topic, payload in messages:
            timing_state.apply_message(state, topic, payload)
        live = timing_state.snapshot(state)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for topic, payload in messages:
                    handle.write(
                        json.dumps({"topic": topic, "payload": payload}) + "\n"
                    )
            replayed = timing_state.replay_jsonl(path)

        self.assertEqual(replayed["drivers"], live["drivers"])
        self.assertEqual(replayed["drivers"][0]["last_lap"], "1:31.500")
        self.assertEqual(replayed["drivers"][0]["sector2"], "39.2")
        self.assertEqual(replayed["drivers"][0]["position"], "1")


if __name__ == "__main__":
    unittest.main()
