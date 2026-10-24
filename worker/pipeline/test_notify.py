"""Notifications are recorded locally and shaped per webhook host."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import notify  # noqa: E402


class PayloadTests(unittest.TestCase):
    def test_discord_gets_content_and_slack_gets_text(self) -> None:
        discord = notify.build_webhook_payload("https://discord.com/api/webhooks/1/x", "Started", "FP3", "info")
        slack = notify.build_webhook_payload("https://hooks.slack.com/services/x", "Started", "FP3", "warning")
        self.assertEqual(discord, {"content": "Started\nFP3"})
        self.assertEqual(slack, {"text": "Warning: Started\nFP3"})


class EventLogTests(unittest.TestCase):
    def test_events_are_appended_and_read_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            env = {"INTERVAL_NOTIFY_WEBHOOK": "", "INTERVAL_NOTIFY_DESKTOP": ""}
            with mock.patch.dict(os.environ, env):
                notify.notify("One", "first", directory=directory)
                notify.notify("Two", "second", level="warning", directory=directory, extra={"pid": 1})
            events = notify.recent_events(directory=directory)
        self.assertEqual([event["title"] for event in events], ["One", "Two"])
        self.assertEqual(events[1]["level"], "warning")
        self.assertEqual(events[1]["extra"], {"pid": 1})

    def test_webhook_failure_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"INTERVAL_NOTIFY_WEBHOOK": "https://hooks.slack.com/services/x", "INTERVAL_NOTIFY_DESKTOP": ""}
            with mock.patch.dict(os.environ, env), mock.patch.object(
                notify.requests, "post", side_effect=notify.requests.RequestException("down")
            ) as post:
                event = notify.notify("Ping", directory=Path(tmp))
            post.assert_called_once()
        self.assertEqual(event["title"], "Ping")


if __name__ == "__main__":
    unittest.main()
