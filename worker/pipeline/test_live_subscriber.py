"""The live subscriber must not open the hub from Cloud Run."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_subscriber  # noqa: E402


class LiveSubscriberGuardTests(unittest.TestCase):
    def test_cloud_run_service_is_refused(self) -> None:
        with mock.patch.dict(os.environ, {"K_SERVICE": "f1-worker"}):
            with self.assertRaises(RuntimeError):
                live_subscriber.assert_not_cloud_run()

    def test_cloud_run_job_is_refused(self) -> None:
        with mock.patch.dict(os.environ, {"CLOUD_RUN_JOB": "f1-import"}, clear=False):
            os.environ.pop("K_SERVICE", None)
            with self.assertRaises(RuntimeError):
                live_subscriber.assert_not_cloud_run()

    def test_main_does_not_connect_on_cloud_run(self) -> None:
        with mock.patch.dict(os.environ, {"K_SERVICE": "f1-worker"}):
            with mock.patch.object(live_subscriber, "LiveSubscriber") as subscriber:
                code = live_subscriber.main([])
        self.assertEqual(code, 1)
        subscriber.assert_not_called()

    def test_replay_does_not_open_the_hub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "topic": "TimingData",
                        "payload": {"Lines": {"1": {"Position": "1"}}},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"K_SERVICE": "f1-worker"}):
                with mock.patch.object(live_subscriber, "LiveSubscriber") as subscriber:
                    code = live_subscriber.main(["--replay", str(path)])
            subscriber.assert_not_called()
            self.assertEqual(code, 0)
            snapshot = json.loads((path.parent / "timing-snapshot.json").read_text())
            self.assertEqual(snapshot["drivers"][0]["position"], "1")


if __name__ == "__main__":
    unittest.main()
