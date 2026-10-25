"""Recording windows come from the schedule; the hub decides the early stop."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_watch  # noqa: E402

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)

SCHEDULE = {
    "year": 2026,
    "events": [
        {
            "eventName": "United States Grand Prix",
            "round": 18,
            "sessions": [
                {"code": "FP1", "label": "Practice 1", "dateUtc": "2026-10-23T17:30:00+00:00"},
                {"code": "FP2", "label": "Practice 2", "dateUtc": "2026-10-23T21:00:00+00:00"},
                {"code": "FP3", "label": "Practice 3", "dateUtc": "2026-10-24T17:30:00+00:00"},
                {"code": "Q", "label": "Qualifying", "dateUtc": "2026-10-24T21:00:00+00:00"},
                {"code": "R", "label": "Race", "dateUtc": "2026-10-25T20:00:00+00:00"},
            ],
        },
        {
            "eventName": "Mexico City Grand Prix",
            "round": 19,
            "sessions": [
                {"code": "FP1", "label": "Practice 1", "dateUtc": "2026-10-30T18:30:00Z"},
                {"code": "R", "label": "Race", "dateUtc": None},
            ],
        },
    ],
}


class WindowTests(unittest.TestCase):
    def test_past_sessions_are_dropped_and_windows_are_ordered(self) -> None:
        windows = live_watch.session_windows(SCHEDULE, lead=timedelta(minutes=60), grace=timedelta(minutes=30), now=NOW)
        self.assertEqual([w.code for w in windows], ["FP3", "Q", "R", "FP1"])
        fp3 = windows[0]
        self.assertEqual(fp3.record_from, datetime(2026, 10, 24, 16, 30, tzinfo=timezone.utc))
        self.assertEqual(fp3.record_until, datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc))
        race = windows[2]
        self.assertEqual(race.record_until, datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc))
        self.assertEqual(windows[3].event, "Mexico City Grand Prix")

    def test_a_session_whose_window_is_still_open_is_kept(self) -> None:
        during_fp2 = datetime(2026, 10, 23, 21, 30, tzinfo=timezone.utc)
        windows = live_watch.session_windows(SCHEDULE, lead=timedelta(minutes=60), grace=timedelta(minutes=30), now=during_fp2)
        self.assertEqual(windows[0].code, "FP2")
        self.assertTrue(windows[0].contains(during_fp2))

    def test_next_skips_recorded_sessions(self) -> None:
        windows = live_watch.session_windows(SCHEDULE, lead=timedelta(minutes=60), grace=timedelta(minutes=30), now=NOW)
        target = live_watch.current_or_next(windows, NOW, done={windows[0].key})
        self.assertEqual(target.code, "Q")
        self.assertIsNone(live_watch.current_or_next(windows, NOW, done={w.key for w in windows}))

    def test_json_view_is_serialisable(self) -> None:
        windows = live_watch.session_windows(SCHEDULE, lead=timedelta(minutes=60), grace=timedelta(minutes=30), now=NOW)
        data = json.loads(json.dumps(windows[0].as_json()))
        self.assertEqual(data["key"], "2026:United States Grand Prix:FP3")
        self.assertEqual(data["starts_at"], "2026-10-24T17:30:00+00:00")


class SnapshotTests(unittest.TestCase):
    def test_only_a_snapshot_written_after_start_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            snap = {"updated_at": "2026-10-24T18:40:00+00:00", "session": {"status": "Finalised"}}
            (directory / "timing-snapshot.json").write_text(json.dumps(snap))
            before = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)
            after = datetime(2026, 10, 24, 19, 0, tzinfo=timezone.utc)
            self.assertEqual(live_watch.snapshot_status(directory, before), "Finalised")
            self.assertIsNone(live_watch.snapshot_status(directory, after))
            self.assertIn("Finalised", live_watch.FINISHED_STATUSES)

    def test_completed_laps_counts_the_lap_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(live_watch.completed_laps(directory), 0)
            (directory / "live-laps.json").write_text(json.dumps({"laps": [{}, {}, {}]}))
            self.assertEqual(live_watch.completed_laps(directory), 3)


class ScheduleCacheTests(unittest.TestCase):
    def test_fresh_cache_is_used_without_fastf1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            live_watch.schedule_path(2026, directory).write_text(json.dumps(SCHEDULE))
            with mock.patch.dict(sys.modules, {"fastf1_schedule": None}):
                loaded = live_watch.load_schedule(2026, directory)
        self.assertEqual(loaded["events"][0]["eventName"], "United States Grand Prix")

    def test_stale_cache_survives_a_failed_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = live_watch.schedule_path(2026, directory)
            path.write_text(json.dumps(SCHEDULE))
            old = (live_watch.utcnow() - timedelta(days=3)).timestamp()
            os.utime(path, (old, old))
            with mock.patch.dict(sys.modules, {"fastf1_schedule": None}):
                loaded = live_watch.load_schedule(2026, directory)
        self.assertEqual(loaded["year"], 2026)

    def test_no_cache_and_no_fastf1_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"fastf1_schedule": None}):
                with self.assertRaises(RuntimeError):
                    live_watch.load_schedule(2026, Path(tmp))


class StateTests(unittest.TestCase):
    def test_state_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(live_watch.load_state(directory), {"recorded": []})
            live_watch.save_state(directory, {"recorded": ["2026:X:R"]})
            self.assertEqual(live_watch.load_state(directory)["recorded"], ["2026:X:R"])
            live_watch.write_status(directory, state="armed")
            status = json.loads((directory / live_watch.STATUS_FILE).read_text())
            self.assertEqual(status["state"], "armed")
            self.assertIn("updated_at", status)

    def test_cloud_run_guard(self) -> None:
        with mock.patch.dict(os.environ, {"K_SERVICE": "x"}):
            with self.assertRaises(RuntimeError):
                live_watch.assert_not_cloud_run()


if __name__ == "__main__":
    unittest.main()
