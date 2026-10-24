"""Replay an official livetiming archive into the live tables.

After a session, F1 publishes StreamPath files under
``livetiming.formula1.com/static``. This reads those files with the F1 TV
bearer and feeds them through the same lap and telemetry writers as the
live hub. It does not open the websocket and it does not write the batch
tables.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import live_laps
import live_telemetry
import live_token
import timing_state

STATIC_ROOT = "https://livetiming.formula1.com/static/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

# Identity feeds are applied before lap and car feeds when timestamps tie.
FEEDS = (
    "SessionInfo.jsonStream",
    "DriverList.jsonStream",
    "TimingAppData.jsonStream",
    "TrackStatus.jsonStream",
    "SessionStatus.jsonStream",
    "TimingData.jsonStream",
    "CarData.z.jsonStream",
    "Position.z.jsonStream",
)


def topic_of(feed: str) -> str:
    return feed[: -len(".jsonStream")] if feed.endswith(".jsonStream") else feed


def parse_stream(text: str) -> list[tuple[str, Any]]:
    """Split one jsonStream into (session clock, payload) records.

    Each line is ``HH:MM:SS.mmm`` plus either a JSON object or a quoted
    base64 zlib blob. The clock is session time, not UTC.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    records: list[tuple[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 13 or line[2] != ":" or line[5] != ":":
            continue
        stamp, body = line[:12], line[12:]
        if body.startswith("{") or body.startswith("["):
            payload: Any = json.loads(body)
        else:
            payload = body
        records.append((stamp, payload))
    return records


def _stamp_key(stamp: str) -> tuple[int, int, int, int]:
    hours, minutes, rest = stamp.split(":")
    seconds, millis = rest.split(".")
    return int(hours), int(minutes), int(seconds), int(millis)


def download_feed(session_path: str, feed: str, token: str) -> str:
    url = f"{STATIC_ROOT}{session_path.strip('/')}/{feed}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8-sig")


def load_messages(session_path: str, token: str) -> list[tuple[str, Any]]:
    ranked: list[tuple[tuple[int, int, int, int], int, str, Any]] = []
    for index, feed in enumerate(FEEDS):
        topic = topic_of(feed)
        try:
            text = download_feed(session_path, feed, token)
        except urllib.error.HTTPError as exc:
            print(f"  {topic}: HTTP {exc.code}, skipped")
            continue
        records = parse_stream(text)
        print(f"  {topic}: {len(records)} record(s)")
        for stamp, payload in records:
            ranked.append((_stamp_key(stamp), index, topic, payload))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [(topic, payload) for _, _, topic, payload in ranked]


def replay_messages(
    messages: list[tuple[str, Any]],
    directory: Path,
    *,
    bigquery: bool = True,
) -> dict[str, int]:
    state = timing_state.new_state()
    laps = live_laps.LapLog(directory, bigquery=bigquery)
    telemetry = live_telemetry.TelemetryLog(directory, bigquery=bigquery)
    if bigquery:
        known_laps = laps.skip_stored()
        known_points, blocked_laps = telemetry.skip_stored()
        print(
            f"  stored already: {known_laps} laps, {known_points} telemetry points, "
            f"{blocked_laps} full laps left unchanged"
        )
    lap_rows = 0
    for index, (topic, payload) in enumerate(messages):
        completed = timing_state.completed_lap_rows(state, topic, payload)
        timing_state.apply_message(state, topic, payload)
        telemetry.observe(state, topic, payload)
        if completed:
            lap_rows += laps.add(completed)
        if index % 400 == 0:
            telemetry.flush()
    telemetry.flush()
    return {
        "messages": len(messages),
        "laps": lap_rows,
        "telemetry": telemetry.inserted,
    }


def replay_session(
    session_path: str,
    directory: Path,
    token: str,
    *,
    bigquery: bool = True,
) -> dict[str, int]:
    print(f"Archive: {session_path}")
    messages = load_messages(session_path, token)
    counts = replay_messages(messages, directory, bigquery=bigquery)
    print(
        f"  replayed {counts['messages']} messages, "
        f"{counts['laps']} new laps, {counts['telemetry']} new telemetry rows"
    )
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay F1 static archives into the live tables")
    parser.add_argument(
        "--path",
        action="append",
        required=True,
        help="Session path from Index.json, for example 2026/.../2026-10-23_Practice_1/",
    )
    parser.add_argument("--dir", type=Path, default=None)
    args = parser.parse_args(argv)
    token_file, _claims = live_token.check_stored()
    token = token_file.read_text().strip()
    directory = args.dir or (Path.home() / ".local" / "share" / "interval" / "live")
    try:
        for session_path in args.path:
            replay_session(session_path, directory, token)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Archive replay failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
