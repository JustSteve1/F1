"""Tell the operator what the live pipeline is doing.

Every event is printed and appended to ``events.jsonl`` in the live
directory, so the ``/live`` page can show the latest one. Optional extras:

- ``INTERVAL_NOTIFY_WEBHOOK``  Slack or Discord incoming-webhook URL
- ``INTERVAL_NOTIFY_DESKTOP=1``  macOS Notification Center or ``notify-send``

Delivery failures are reported on stderr and never raise: a notification
must not take the recording down with it.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

LEVELS = ("info", "warning", "error")
_lock = threading.Lock()


def live_dir() -> Path:
    override = os.environ.get("INTERVAL_LIVE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "interval" / "live"


def events_path(directory: Path | None = None) -> Path:
    return (directory or live_dir()) / "events.jsonl"


def build_webhook_payload(url: str, title: str, message: str, level: str) -> dict[str, Any]:
    """Discord wants ``content``; Slack and most relays want ``text``."""
    prefix = {"warning": "Warning: ", "error": "Error: "}.get(level, "")
    text = f"{prefix}{title}\n{message}" if message else f"{prefix}{title}"
    if "discord.com/api/webhooks" in url or "discordapp.com/api/webhooks" in url:
        return {"content": text[:1900]}
    return {"text": text}


def _desktop(title: str, message: str) -> None:
    system = platform.system()
    if system == "Darwin":
        script = (
            f'display notification {json.dumps(message)} '
            f'with title {json.dumps("Interval live")} subtitle {json.dumps(title)}'
        )
        subprocess.run(["osascript", "-e", script], check=False, timeout=10, capture_output=True)
    elif system == "Linux":
        subprocess.run(["notify-send", f"Interval live: {title}", message], check=False, timeout=10, capture_output=True)


def notify(
    title: str,
    message: str = "",
    *,
    level: str = "info",
    directory: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record one event everywhere that is configured. Returns the event."""
    if level not in LEVELS:
        level = "info"
    event: dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "title": title,
        "message": message,
    }
    if extra:
        event["extra"] = extra

    stream = sys.stderr if level == "error" else sys.stdout
    print(f"[{event['at']}] {level.upper()}: {title}" + (f" — {message}" if message else ""), file=stream, flush=True)

    try:
        path = events_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, default=str) + "\n")
    except OSError as exc:
        print(f"notify: could not append to events.jsonl ({exc})", file=sys.stderr)

    webhook = os.environ.get("INTERVAL_NOTIFY_WEBHOOK")
    if webhook:
        try:
            response = requests.post(webhook, json=build_webhook_payload(webhook, title, message, level), timeout=10)
            if response.status_code >= 400:
                print(f"notify: webhook returned HTTP {response.status_code}", file=sys.stderr)
        except requests.RequestException as exc:
            print(f"notify: webhook failed ({exc})", file=sys.stderr)

    if os.environ.get("INTERVAL_NOTIFY_DESKTOP") == "1":
        try:
            _desktop(title, message)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"notify: desktop notification failed ({exc})", file=sys.stderr)

    return event


def recent_events(limit: int = 20, directory: Path | None = None) -> list[dict[str, Any]]:
    path = events_path(directory)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


if __name__ == "__main__":
    notify(" ".join(sys.argv[1:]) or "Test notification", "Sent from notify.py")
