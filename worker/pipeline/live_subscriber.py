"""Subscribe to Formula 1 livetiming SignalR Core.

Records every feed message as JSONL and keeps a merged timing snapshot.
Does not import FastF1 and does not call OpenF1.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from signalrcore.hub_connection_builder import HubConnectionBuilder

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_laps  # noqa: E402
import live_telemetry  # noqa: E402
import live_token  # noqa: E402
import timing_state  # noqa: E402

NEGOTIATE_URL = "https://livetiming.formula1.com/signalrcore/negotiate"
HUB_URL = "wss://livetiming.formula1.com/signalrcore"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

TIMING_TOPICS = [
    "Heartbeat",
    "SessionInfo",
    "SessionStatus",
    "DriverList",
    "TimingData",
    "TimingAppData",
    "TimingStats",
    "TrackStatus",
    "WeatherData",
    "RaceControlMessages",
    "LapCount",
    "ExtrapolatedClock",
    "CarData.z",
    "Position.z",
]

SNAPSHOT_TOPICS = {
    "TimingData",
    "DriverList",
    "SessionInfo",
    "SessionStatus",
    "ExtrapolatedClock",
    "TrackStatus",
    "LapCount",
    "Heartbeat",
}


def archive_dir() -> Path:
    override = os.environ.get("INTERVAL_LIVE_DIR")
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "interval" / "live"


def assert_not_cloud_run() -> None:
    if os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"):
        raise RuntimeError(
            "Refusing to start on Cloud Run. Livetiming blocks datacenter IPs; "
            "run this on a home or residential connection."
        )


def iter_feed_items(message: Any) -> list[tuple[str, Any]]:
    """Normalise SignalR feed callbacks into (topic, payload) pairs."""
    if hasattr(message, "result") and isinstance(getattr(message, "result"), dict):
        return [(str(topic), payload) for topic, payload in message.result.items()]

    if isinstance(message, (list, tuple)):
        if (
            len(message) >= 2
            and isinstance(message[0], str)
            and not isinstance(message[1], (list, tuple))
        ):
            return [(message[0], message[1])]
        items: list[tuple[str, Any]] = []
        for entry in message:
            items.extend(iter_feed_items(entry))
        return items

    if isinstance(message, dict):
        arguments = message.get("A")
        if isinstance(arguments, list):
            return iter_feed_items(arguments)
        known = [(key, value) for key, value in message.items() if key in TIMING_TOPICS]
        if known:
            return known
    return []


class JsonlArchive:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = self.directory / f"{stamp}-live.jsonl"
        self.snapshot_path = self.directory / "timing-snapshot.json"
        self._handle = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()

    def append(self, topic: str, payload: Any) -> None:
        record = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "topic": topic,
            "payload": payload,
        }
        line = json.dumps(record, separators=(",", ":"), default=str)
        with self._lock:
            self._handle.write(line + "\n")
            self._handle.flush()

    def write_snapshot(self, snap: dict[str, Any]) -> None:
        text = json.dumps(snap, indent=2, default=str)
        temporary = self.snapshot_path.with_suffix(".json.tmp")
        with self._lock:
            temporary.write_text(text)
            temporary.replace(self.snapshot_path)

    def close(self) -> None:
        with self._lock:
            self._handle.close()


class TopicRates:
    def __init__(self) -> None:
        self._times: dict[str, list[float]] = defaultdict(list)

    def add(self, topic: str) -> None:
        self._times[topic].append(time.monotonic())

    def report(self) -> list[str]:
        lines = []
        topics = list(TIMING_TOPICS)
        for extra in self._times:
            if extra not in topics:
                topics.append(extra)
        for topic in topics:
            times = self._times.get(topic) or []
            if not times:
                lines.append(f"{topic}: silent")
                continue
            if len(times) < 2:
                lines.append(f"{topic}: {len(times)} message(s), median gap n/a, n/a")
                continue
            gaps = [times[index] - times[index - 1] for index in range(1, len(times))]
            gaps.sort()
            median_ms = gaps[len(gaps) // 2] * 1000
            span = times[-1] - times[0]
            rate = (len(times) / span) if span > 0 else 0
            lines.append(
                f"{topic}: {len(times)} message(s), median gap {median_ms:.0f} ms, {rate:.2f} Hz"
            )
        return lines


class LiveSubscriber:
    def __init__(self, token: str, directory: Path):
        self._token = token
        self.archive = JsonlArchive(directory)
        self.laps = live_laps.LapLog(directory)
        self.telemetry = live_telemetry.TelemetryLog(directory)
        self.state = timing_state.new_state()
        self.rates = TopicRates()
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._connection = None
        self._error: str | None = None

    def _on_error(self, message: Any) -> None:
        self._error = str(message)
        print(f"SignalR error: {message}", file=sys.stderr)

    def _handle(self, message: Any) -> None:
        items = iter_feed_items(message)
        if not items:
            return
        for topic, payload in items:
            self.archive.append(topic, payload)
            self.rates.add(topic)
            with self._lock:
                completed = timing_state.completed_lap_rows(self.state, topic, payload)
                timing_state.apply_message(self.state, topic, payload)
                self.telemetry.observe(self.state, topic, payload)
                snap = timing_state.snapshot(self.state) if topic in SNAPSHOT_TOPICS else None
            if completed:
                self.laps.add(completed)
            if snap is not None:
                self.archive.write_snapshot(snap)

    def _negotiate_headers(self) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT}
        # OPTIONS is 405 on the current hub, but the response still sets the
        # load-balancer cookie SignalR needs before the websocket opens.
        response = requests.options(NEGOTIATE_URL, headers=headers, timeout=20)
        cookie = response.cookies.get("AWSALBCORS")
        if cookie:
            headers["Cookie"] = f"AWSALBCORS={cookie}"
        elif response.status_code >= 400:
            response.raise_for_status()
        else:
            print(
                "Negotiate did not return AWSALBCORS; connecting without it.",
                file=sys.stderr,
            )
        return headers

    def connect(self) -> None:
        headers = self._negotiate_headers()
        options = {
            "verify_ssl": True,
            "access_token_factory": lambda: self._token,
            "headers": headers,
        }
        connection = (
            HubConnectionBuilder()
            .with_url(HUB_URL, options=options)
            .configure_logging(logging.WARNING)
            .build()
        )
        connection.on_open(lambda: self._connected.set())
        connection.on_close(lambda: self._connected.clear())
        connection.on_error(self._on_error)
        connection.on("feed", self._handle)
        self._connection = connection
        connection.start()
        if not self._connected.wait(timeout=20):
            detail = f" Last error: {self._error}" if self._error else ""
            raise RuntimeError("SignalR connection was not established within 20s." + detail)
        connection.send("Subscribe", [TIMING_TOPICS], on_invocation=self._handle)

    def stop(self) -> None:
        self.telemetry.flush()
        if self._connection is not None:
            self._connection.stop()
        self.archive.close()


def run_replay(path: Path) -> int:
    snap = timing_state.replay_jsonl(path)
    destination = path.parent / "timing-snapshot.json"
    destination.write_text(json.dumps(snap, indent=2, default=str))
    laps = timing_state.replay_laps(path)
    laps_path = path.parent / "live-laps.json"
    laps_path.write_text(json.dumps({"laps": laps}, indent=2, default=str))
    print(f"Replayed {path}")
    print(f"Snapshot: {destination}")
    print(f"Drivers: {len(snap['drivers'])}")
    print(f"Completed laps: {len(laps)} -> {laps_path}")
    session = snap.get("session") or {}
    print(f"Session: {session.get('meeting') or session.get('name') or '(none)'}")
    return 0


def run_live(seconds: int | None, directory: Path) -> int:
    assert_not_cloud_run()
    path, claims = live_token.check_stored()
    print(live_token.format_status(claims, path))
    token = path.read_text().strip()
    subscriber = LiveSubscriber(token, directory)
    print(f"Connecting to {HUB_URL}")
    subscriber.connect()
    print(f"Subscribed. Archive: {subscriber.archive.path}")
    print(f"Snapshot: {subscriber.archive.snapshot_path}")
    print(f"Laps: {subscriber.laps.path}")
    if subscriber.laps.bigquery_ready:
        print(f"BigQuery laps: {live_laps.table_id()}")
    else:
        print(f"BigQuery laps: not writing ({subscriber.laps.bigquery_error})")
    if subscriber.telemetry.bigquery_ready:
        print(f"BigQuery telemetry: {live_telemetry.table_id()}")
    else:
        print(f"BigQuery telemetry: not writing ({subscriber.telemetry.bigquery_error})")
    started = time.monotonic()
    try:
        while True:
            time.sleep(5)
            subscriber.telemetry.flush()
            elapsed = time.monotonic() - started
            heard = sum(len(times) for times in subscriber.rates._times.values())
            print(
                f"t={elapsed:.0f}s messages={heard} "
                f"telemetry={subscriber.telemetry.inserted}"
            )
            if seconds is not None and elapsed >= seconds:
                break
    except KeyboardInterrupt:
        print("Stopping.")
    finally:
        subscriber.stop()
    print("Topic rates:")
    for line in subscriber.rates.report():
        print(line)
    print(f"Archive: {subscriber.archive.path}")
    print(f"Snapshot: {subscriber.archive.snapshot_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record F1 livetiming and merge TimingData")
    parser.add_argument(
        "--seconds",
        type=int,
        default=None,
        help="Stop after this many seconds. Default: run until Ctrl-C.",
    )
    parser.add_argument(
        "--replay",
        type=Path,
        default=None,
        help="Rebuild timing-snapshot.json from a JSONL archive and exit.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Archive directory. Default: ~/.local/share/interval/live",
    )
    args = parser.parse_args(argv)
    try:
        if args.replay is not None:
            return run_replay(args.replay)
        return run_live(args.seconds, args.dir or archive_dir())
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Live subscriber failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
