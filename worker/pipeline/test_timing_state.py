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

    def _session(self, state: dict) -> None:
        timing_state.apply_message(
            state,
            "SessionInfo",
            {
                "Name": "Race",
                "Type": "Race",
                "Path": "2026/2026-10-04_Bahrain_Grand_Prix/2026-10-04_Race",
                "Meeting": {"Name": "Bahrain Grand Prix"},
            },
        )
        timing_state.apply_message(
            state,
            "DriverList",
            {"1": {"Tla": "NOR", "TeamName": "McLaren"}},
        )
        timing_state.apply_message(
            state,
            "TimingAppData",
            {"Lines": {"1": {"Stints": [{"Compound": "SOFT", "TotalLaps": 6, "New": "false"}]}}},
        )
        timing_state.apply_message(state, "TrackStatus", {"Status": "1", "Message": "AllClear"})

    def test_completed_lap_matches_batch_columns_and_keeps_sectors(self) -> None:
        state = timing_state.new_state()
        self._session(state)
        timing_state.apply_message(
            state,
            "TimingData",
            {
                "Lines": {
                    "1": {
                        "NumberOfLaps": 4,
                        "Position": "2",
                        "Sectors": [
                            {"Value": "28.1"},
                            {"Value": "39.4"},
                            {"Value": "24.6"},
                        ],
                        "Speeds": {"I1": {"Value": "289"}, "I2": {"Value": "305"}, "ST": {"Value": "321"}},
                    }
                }
            },
        )
        completing = {
            "Lines": {
                "1": {
                    "NumberOfLaps": 5,
                    "Position": "1",
                    "LastLapTime": {"Value": "1:32.100", "PersonalFastest": True},
                    "Sectors": {"0": {"Segments": {"1": {"Status": 2048}}}},
                }
            }
        }
        rows = timing_state.completed_lap_rows(state, "TimingData", completing)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(tuple(row), timing_state.LAP_COLUMNS)
        self.assertEqual(row["driver_number"], "1")
        self.assertEqual(row["driver_code"], "NOR")
        self.assertEqual(row["team"], "McLaren")
        self.assertEqual(row["lap_number"], 5)
        self.assertEqual(row["position"], 1)
        self.assertAlmostEqual(row["lap_duration"], 92.1)
        self.assertAlmostEqual(row["sector_1_time"], 28.1)
        self.assertAlmostEqual(row["sector_2_time"], 39.4)
        self.assertAlmostEqual(row["sector_3_time"], 24.6)
        self.assertEqual(row["speed_i1"], 289)
        self.assertEqual(row["compound"], "SOFT")
        self.assertEqual(row["tyre_age_laps"], 6)
        self.assertEqual(row["stint_number"], 1)
        self.assertIs(row["fresh_tyre"], False)
        self.assertIs(row["is_personal_best"], True)
        self.assertEqual(row["track_status"], "1")
        self.assertEqual(row["session_type"], "R")
        self.assertEqual(row["season"], 2026)
        self.assertEqual(row["event_name"], "Bahrain Grand Prix")
        self.assertIsInstance(row["session_key"], int)
        self.assertEqual(row["meeting_key"], row["session_key"])
        self.assertIsNone(row["pit_in_time"])
        self.assertIsNone(row["fastf1_generated"])

        timing_state.apply_message(state, "TimingData", completing)
        self.assertEqual(timing_state.completed_lap_rows(state, "TimingData", completing), [])

    def test_same_lap_in_a_replay_is_kept_once(self) -> None:
        messages = [
            (
                "SessionInfo",
                {
                    "Name": "Race",
                    "Type": "Race",
                    "Path": "2026/2026-10-04_Bahrain_Grand_Prix/2026-10-04_Race",
                    "Meeting": {"Name": "Bahrain Grand Prix"},
                },
            ),
            (
                "TimingData",
                {
                    "Lines": {
                        "44": {
                            "NumberOfLaps": 2,
                            "LastLapTime": {"Value": "1:31.500"},
                            "Sectors": [{"Value": "28.0"}, {"Value": "39.0"}, {"Value": "24.5"}],
                        }
                    }
                },
            ),
            (
                "TimingData",
                {
                    "Lines": {
                        "44": {
                            "NumberOfLaps": 2,
                            "Sectors": {"0": {"Segments": {"0": {"Status": 2048}}}},
                        }
                    }
                },
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "laps.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for topic, payload in messages:
                    handle.write(json.dumps({"topic": topic, "payload": payload}) + "\n")
            laps = timing_state.replay_laps(path)
        self.assertEqual(len(laps), 1)
        self.assertEqual(laps[0]["lap_number"], 2)
        self.assertAlmostEqual(laps[0]["sector_1_time"], 28.0)


if __name__ == "__main__":
    unittest.main()
