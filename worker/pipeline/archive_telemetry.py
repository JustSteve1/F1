"""Build 0.5s lap telemetry from an F1 static livetiming archive.

The live subscriber records TimingData only. CarData.z and Position.z are
published on the static archive after the session. This module turns those
streams into telemetry rows the laps_kaggle view can join.

Kaggle telemetry is one JSON object every 0.5s:

    {"brake":0,"drs":0,"gear":7,"rpm":11194,"speed":294,"t":0.0,
     "throttle":100,"x":-1135.7,"y":-1389.7,"z":85.2}

The view builds that JSON. Rows here are the telemetry-table grain: t = 0.0,
0.5, 1.0, ... Position arrives in tenths of a metre. Throttle and brake use
104 as full-scale, which is capped to 100 / on.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import zlib
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SAMPLE_SEC = 0.5
# Car packets are about 4 Hz. A sample further away than this is a gap.
NEAREST_TOLERANCE_SEC = 0.45

_LINE = re.compile(r"^(?P<h>\d+):(?P<m>\d+):(?P<s>\d+(?:\.\d+)?)(?P<body>.*)$")


def _raw_inflate(payload: str) -> Any:
    data = base64.b64decode(payload.strip().strip('"'))
    return json.loads(zlib.decompress(data, wbits=-15))


def parse_stream_line(line: str) -> tuple[float, Any] | None:
    """Return (offset seconds, payload) for one livetiming stream line."""
    text = line.strip().lstrip("\ufeff")
    if not text:
        return None
    match = _LINE.match(text)
    if match is None:
        return None
    offset = (
        int(match.group("h")) * 3600
        + int(match.group("m")) * 60
        + float(match.group("s"))
    )
    body = match.group("body")
    if body.startswith('"'):
        try:
            return offset, _raw_inflate(body[1:])
        except Exception:
            return None
    if body.startswith("{"):
        try:
            return offset, json.loads(body)
        except json.JSONDecodeError:
            return None
    return None


def iter_stream(path: Path | str):
    with open(path, encoding="utf-8-sig") as handle:
        for line in handle:
            parsed = parse_stream_line(line)
            if parsed is not None:
                yield parsed


def _parse_utc(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clock_seconds(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("Value")
    if not isinstance(value, str) or not value.strip():
        return None
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return float(parts[0])
    except ValueError:
        return None


def _cap_pedal(value: Any) -> int | None:
    """F1 sends 104 for a fully pressed pedal. Kaggle uses 0-100."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, number))


def utc_base(car_path: Path | str) -> datetime:
    """Archive offset 0 as a UTC instant, from the first car packet."""
    for offset, payload in iter_stream(car_path):
        entries = payload.get("Entries") if isinstance(payload, dict) else None
        if not entries:
            continue
        utc = entries[0].get("Utc")
        if not utc:
            continue
        return _parse_utc(utc) - timedelta(seconds=offset)
    raise RuntimeError(f"No CarData timestamps in {car_path}")


def car_series(car_path: Path | str) -> dict[str, list[tuple[datetime, dict[str, Any]]]]:
    """Per driver, time-ordered RPM / speed / gear / throttle / brake samples."""
    series: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}
    for _offset, payload in iter_stream(car_path):
        if not isinstance(payload, dict):
            continue
        for entry in payload.get("Entries") or []:
            utc_text = entry.get("Utc")
            cars = entry.get("Cars")
            if not utc_text or not isinstance(cars, dict):
                continue
            instant = _parse_utc(utc_text)
            for number, body in cars.items():
                channels = body.get("Channels") if isinstance(body, dict) else None
                if not isinstance(channels, dict):
                    continue
                throttle = _cap_pedal(channels.get("4"))
                brake_pedal = _cap_pedal(channels.get("5"))
                sample = {
                    "rpm": channels.get("0"),
                    "speed": channels.get("2"),
                    "gear": channels.get("3"),
                    "throttle": throttle,
                    "brake": bool(brake_pedal) if brake_pedal is not None else None,
                }
                series.setdefault(str(number), []).append((instant, sample))
    for samples in series.values():
        samples.sort(key=lambda item: item[0])
    return series


def position_series(position_path: Path | str) -> dict[str, list[tuple[datetime, dict[str, float]]]]:
    """Per driver, XYZ in metres. The archive stores tenths of a metre."""
    series: dict[str, list[tuple[datetime, dict[str, float]]]] = {}
    for _offset, payload in iter_stream(position_path):
        if not isinstance(payload, dict):
            continue
        for entry in payload.get("Position") or []:
            utc_text = entry.get("Timestamp")
            entries = entry.get("Entries")
            if not utc_text or not isinstance(entries, dict):
                continue
            instant = _parse_utc(utc_text)
            for number, body in entries.items():
                if not isinstance(body, dict):
                    continue
                try:
                    point = {
                        "x": float(body["X"]) / 10.0,
                        "y": float(body["Y"]) / 10.0,
                        "z": float(body["Z"]) / 10.0,
                    }
                except (KeyError, TypeError, ValueError):
                    continue
                series.setdefault(str(number), []).append((instant, point))
    for samples in series.values():
        samples.sort(key=lambda item: item[0])
    return series


def lap_windows(timing_path: Path | str, base: datetime) -> list[dict[str, Any]]:
    """One window per finished lap. Lap N starts when lap N-1 is counted."""
    ends: dict[str, list[tuple[int, float, float | None]]] = {}
    seen: dict[str, int] = {}
    for offset, payload in iter_stream(timing_path):
        if not isinstance(payload, dict):
            continue
        lines = payload.get("Lines")
        if not isinstance(lines, dict):
            continue
        for number, patch in lines.items():
            if not isinstance(patch, dict) or "NumberOfLaps" not in patch:
                continue
            try:
                lap_number = int(patch["NumberOfLaps"])
            except (TypeError, ValueError):
                continue
            driver = str(number)
            if lap_number <= seen.get(driver, 0):
                continue
            seen[driver] = lap_number
            ends.setdefault(driver, []).append(
                (lap_number, offset, _clock_seconds(patch.get("LastLapTime")))
            )

    windows: list[dict[str, Any]] = []
    for driver, events in ends.items():
        events.sort(key=lambda item: item[0])
        by_lap = {lap: (offset, clock) for lap, offset, clock in events}
        for lap_number, end_offset, clock in events:
            previous = by_lap.get(lap_number - 1)
            if previous is None:
                continue
            start_offset = previous[0]
            if end_offset <= start_offset:
                continue
            windows.append(
                {
                    "driver_number": driver,
                    "lap_number": lap_number,
                    "start": base + timedelta(seconds=start_offset),
                    "end": base + timedelta(seconds=end_offset),
                    "clock_seconds": clock,
                }
            )
    return windows


def _nearest(samples: list[tuple[datetime, Any]], target: datetime, tolerance: float):
    if not samples:
        return None
    times = [item[0] for item in samples]
    index = bisect_left(times, target)
    best = None
    best_gap = tolerance
    for probe in (index - 1, index):
        if probe < 0 or probe >= len(samples):
            continue
        gap = abs((samples[probe][0] - target).total_seconds())
        if gap <= best_gap:
            best_gap = gap
            best = samples[probe][1]
    return best


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def decode_feed_payload(payload: Any) -> Any | None:
    """Inflate a live or archive car packet. Dicts pass through."""
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None
    text = payload.strip().strip('"')
    if not text:
        return None
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    try:
        return _raw_inflate(text)
    except Exception:
        return None


def car_samples_from_payload(payload: Any) -> list[tuple[str, datetime, dict[str, Any]]]:
    """(driver, utc, channels) from one CarData.z packet."""
    decoded = decode_feed_payload(payload)
    if not isinstance(decoded, dict):
        return []
    samples: list[tuple[str, datetime, dict[str, Any]]] = []
    for entry in decoded.get("Entries") or []:
        utc_text = entry.get("Utc") if isinstance(entry, dict) else None
        cars = entry.get("Cars") if isinstance(entry, dict) else None
        if not utc_text or not isinstance(cars, dict):
            continue
        instant = _parse_utc(utc_text)
        for number, body in cars.items():
            channels = body.get("Channels") if isinstance(body, dict) else None
            if not isinstance(channels, dict):
                continue
            throttle = _cap_pedal(channels.get("4"))
            brake_pedal = _cap_pedal(channels.get("5"))
            samples.append(
                (
                    str(number),
                    instant,
                    {
                        "rpm": channels.get("0"),
                        "speed": channels.get("2"),
                        "gear": channels.get("3"),
                        "throttle": throttle,
                        "brake": bool(brake_pedal) if brake_pedal is not None else None,
                    },
                )
            )
    return samples


def position_samples_from_payload(payload: Any) -> list[tuple[str, datetime, dict[str, float]]]:
    """(driver, utc, xyz metres) from one Position.z packet."""
    decoded = decode_feed_payload(payload)
    if not isinstance(decoded, dict):
        return []
    samples: list[tuple[str, datetime, dict[str, float]]] = []
    for entry in decoded.get("Position") or []:
        utc_text = entry.get("Timestamp") if isinstance(entry, dict) else None
        entries = entry.get("Entries") if isinstance(entry, dict) else None
        if not utc_text or not isinstance(entries, dict):
            continue
        instant = _parse_utc(utc_text)
        for number, body in entries.items():
            if not isinstance(body, dict):
                continue
            try:
                point = {
                    "x": float(body["X"]) / 10.0,
                    "y": float(body["Y"]) / 10.0,
                    "z": float(body["Z"]) / 10.0,
                }
            except (KeyError, TypeError, ValueError):
                continue
            samples.append((str(number), instant, point))
    return samples


def sample_lap(
    window: dict[str, Any],
    cars: list[tuple[datetime, dict[str, Any]]],
    positions: list[tuple[datetime, dict[str, float]]],
    interval: float = SAMPLE_SEC,
    tolerance: float = NEAREST_TOLERANCE_SEC,
) -> list[dict[str, Any]]:
    """Nearest car and position sample on a fixed grid from the lap start."""
    start = window["start"]
    end = window["end"]
    duration = (end - start).total_seconds()
    points: list[dict[str, Any]] = []
    previous_speed: float | None = None
    cumulative = 0.0
    step = 0
    while True:
        t = round(step * interval, 1)
        if t - duration > 1e-6:
            break
        instant = start + timedelta(seconds=t)
        car = _nearest(cars, instant, tolerance) or {}
        pos = _nearest(positions, instant, tolerance) or {}
        speed = _number(car.get("speed"))
        if speed is None and not pos:
            step += 1
            continue
        delta = 0.0
        if speed is not None and previous_speed is not None and interval:
            delta = (speed - previous_speed) / interval
        distance = (speed / 3.6) * interval if speed is not None else 0.0
        cumulative += distance
        gear = _number(car.get("gear"))
        rpm = _number(car.get("rpm"))
        points.append(
            {
                "driver_number": str(window["driver_number"]),
                "lap_number": int(window["lap_number"]),
                "lap_time_sec": t,
                "interval_sec": interval,
                "speed": speed,
                "throttle": car.get("throttle"),
                "brake": car.get("brake"),
                "gear": int(gear) if gear is not None else None,
                "rpm": rpm,
                "drs": 0,
                "x": pos.get("x"),
                "y": pos.get("y"),
                "z": pos.get("z"),
                "deceleration": round(delta, 2),
                "distance_m": round(distance, 2),
                "cumulative_distance": round(cumulative, 2),
                "date": instant.isoformat(),
            }
        )
        if speed is not None:
            previous_speed = speed
        step += 1
    return points


def build_telemetry(
    directory: Path | str,
    *,
    session_key: int,
    season: int,
    event_name: str,
    session_type: str,
    circuit: str,
    meeting_key: int | None = None,
) -> list[dict[str, Any]]:
    """Telemetry rows for every lap whose start and finish are both in TimingData."""
    root = Path(directory)
    base = utc_base(root / "CarData.z.jsonStream")
    cars = car_series(root / "CarData.z.jsonStream")
    positions = position_series(root / "Position.z.jsonStream")
    windows = lap_windows(root / "TimingData.jsonStream", base)
    imported_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for window in windows:
        driver = str(window["driver_number"])
        for point in sample_lap(window, cars.get(driver, []), positions.get(driver, [])):
            point.update(
                {
                    "session_key": int(session_key),
                    "meeting_key": int(meeting_key if meeting_key is not None else session_key),
                    "season": int(season),
                    "event_name": event_name,
                    "session_type": session_type,
                    "circuit": circuit,
                    "imported_at": imported_at,
                }
            )
            rows.append(point)
    return rows


def upload_rows(client: Any, table: str, rows: list[dict[str, Any]], batch_size: int = 1000) -> int:
    uploaded = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        errors = client.insert_rows_json(table, batch)
        if errors:
            raise RuntimeError(f"BigQuery insert failed at row {start}: {errors[:2]}")
        uploaded += len(batch)
    return uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Load static-archive telemetry into BigQuery")
    parser.add_argument("directory", help="Folder with CarData.z, Position.z, and TimingData streams")
    parser.add_argument("--session-key", type=int, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--session-type", required=True)
    parser.add_argument("--circuit", required=True)
    parser.add_argument("--meeting-key", type=int)
    parser.add_argument("--project", default="f1-data-library")
    parser.add_argument("--dataset", default="f1_data_library_DS")
    args = parser.parse_args()

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project)
    table = f"{args.project}.{args.dataset}.telemetry"
    existing = list(
        client.query(
            f"SELECT COUNT(*) AS n FROM `{table}` WHERE session_key = {int(args.session_key)}",
            location="EU",
        ).result()
    )[0]["n"]
    if existing:
        raise SystemExit(f"{existing} telemetry rows already exist for session {args.session_key}")

    rows = build_telemetry(
        args.directory,
        session_key=args.session_key,
        season=args.season,
        event_name=args.event_name,
        session_type=args.session_type,
        circuit=args.circuit,
        meeting_key=args.meeting_key,
    )
    if not rows:
        raise SystemExit("No telemetry rows built")
    uploaded = upload_rows(client, table, rows)
    laps = len({(row["driver_number"], row["lap_number"]) for row in rows})
    print(f"Uploaded {uploaded} samples across {laps} laps to {table}")


if __name__ == "__main__":
    main()
