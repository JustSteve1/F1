"""Write live car and position samples into telemetry_live.

CarData.z and Position.z are separate feeds. This merges the latest sample
from each onto a 0.5s grid, which is the telemetry array the export view
builds: t, speed, throttle, brake, gear, rpm, drs, x, y, z.

Rows go to telemetry_live only. The batch telemetry table is never written.
"""

from __future__ import annotations

import base64
import json
import math
import os
import threading
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import timing_state

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
TABLE = "telemetry_live"
INTERVAL_SEC = 0.5
# Coordinates since 2020 are tenths of a metre. The export rounds to 0.1 m.
POSITION_SCALE = 10.0
MAX_CATCHUP = 8

CAR_CHANNELS = {
    "rpm": "0",
    "speed": "2",
    "gear": "3",
    "throttle": "4",
    "brake": "5",
    "drs": "45",
}


def table_id() -> str:
    return f"{PROJECT}.{DATASET}.{TABLE}"


def source_table_id() -> str:
    return f"{PROJECT}.{DATASET}.telemetry"


def decode_z(payload: Any) -> dict[str, Any] | None:
    """Inflate a Position.z or CarData.z payload the way FastF1 does."""
    if isinstance(payload, dict):
        if "Position" in payload or "Entries" in payload:
            return payload
        for key in ("Position.z", "CarData.z"):
            if key in payload:
                return decode_z(payload[key])
        return None
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", errors="replace")
    if not isinstance(payload, str) or not payload.strip():
        return None
    text = payload.strip()
    if text[0] == '"':
        text = text.strip('"')
    if text[0] in "{[":
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else None
    inflated = zlib.decompress(base64.b64decode(text), -zlib.MAX_WBITS)
    loaded = json.loads(inflated.decode("utf-8-sig"))
    return loaded if isinstance(loaded, dict) else None


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "." in text:
        head, rest = text.split(".", 1)
        sign = ""
        for marker in ("+", "-"):
            if marker in rest:
                frac, zone = rest.split(marker, 1)
                sign = marker + zone
                rest = frac
                break
        rest = "".join(ch for ch in rest if ch.isdigit())
        text = f"{head}.{(rest + '000000')[:6]}{sign or '+00:00'}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def car_samples(payload: Any) -> list[dict[str, Any]]:
    decoded = decode_z(payload)
    if not decoded:
        return []
    entries = decoded.get("Entries")
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        return []
    samples: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        when = _parse_utc(entry.get("Utc")) or datetime.now(timezone.utc)
        cars = entry.get("Cars")
        if not isinstance(cars, dict):
            continue
        for driver, car in cars.items():
            if not isinstance(car, dict):
                continue
            channels = car.get("Channels")
            if not isinstance(channels, dict):
                continue
            brake = _number(channels.get(CAR_CHANNELS["brake"]))
            drs = _number(channels.get(CAR_CHANNELS["drs"]))
            samples.append(
                {
                    "driver": str(driver),
                    "at": when,
                    "rpm": _number(channels.get(CAR_CHANNELS["rpm"])),
                    "speed": _number(channels.get(CAR_CHANNELS["speed"])),
                    "gear": _number(channels.get(CAR_CHANNELS["gear"])),
                    "throttle": _number(channels.get(CAR_CHANNELS["throttle"])),
                    "brake": None if brake is None else brake > 0,
                    "drs": 0 if drs is None else int(drs),
                }
            )
    return samples


def position_samples(payload: Any) -> list[dict[str, Any]]:
    decoded = decode_z(payload)
    if not decoded:
        return []
    positions = decoded.get("Position")
    if isinstance(positions, dict):
        positions = list(positions.values())
    if not isinstance(positions, list):
        return []
    samples: list[dict[str, Any]] = []
    for sample in positions:
        if not isinstance(sample, dict):
            continue
        when = _parse_utc(sample.get("Timestamp")) or datetime.now(timezone.utc)
        entries = sample.get("Entries")
        if not isinstance(entries, dict):
            continue
        for driver, entry in entries.items():
            if not isinstance(entry, dict) or "X" not in entry:
                continue
            x = _number(entry.get("X"))
            y = _number(entry.get("Y"))
            z = _number(entry.get("Z"))
            if x is None or y is None or z is None:
                continue
            samples.append(
                {
                    "driver": str(driver),
                    "at": when,
                    "x": x / POSITION_SCALE,
                    "y": y / POSITION_SCALE,
                    "z": z / POSITION_SCALE,
                }
            )
    return samples


def _current_lap(state: dict[str, Any], driver: str) -> int:
    line = (state.get("lines") or {}).get(driver) or {}
    completed = timing_state._lap_count(line) or 0
    return completed + 1


def _circuit(info: dict[str, Any]) -> str | None:
    meeting = info.get("Meeting") if isinstance(info.get("Meeting"), dict) else {}
    location = meeting.get("Location")
    if isinstance(location, str) and location.strip():
        return location.strip()
    circuit = meeting.get("Circuit") if isinstance(meeting.get("Circuit"), dict) else {}
    short = circuit.get("ShortName")
    if isinstance(short, str) and short.strip():
        return short.strip()
    return None


class TelemetryLog:
    def __init__(self, directory: Path, *, bigquery: bool = True):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._car: dict[str, dict[str, Any]] = {}
        self._pos: dict[str, dict[str, Any]] = {}
        self._origin: dict[str, tuple[int, datetime]] = {}
        self._next_t: dict[str, float] = {}
        self._prev_speed: dict[str, float | None] = {}
        self._cumulative: dict[str, float] = {}
        self._pending: list[dict[str, Any]] = []
        self._seen: set[str] = set()
        self.inserted = 0
        self._bq_ready = False
        self._bq_error: str | None = None
        self._client: Any = None
        if bigquery:
            self._prepare_bigquery()

    def _prepare_bigquery(self) -> None:
        try:
            from google.cloud import bigquery
        except ImportError:
            self._bq_error = "google-cloud-bigquery is not installed"
            print(f"Live telemetry: {self._bq_error}.")
            return
        try:
            self._client = bigquery.Client(project=PROJECT)
            job = self._client.query(
                f"CREATE TABLE IF NOT EXISTS `{table_id()}` LIKE `{source_table_id()}`"
            )
            job.result()
            self._bq_ready = True
        except Exception as exc:  # noqa: BLE001 — missing credentials must not stop the feed
            self._bq_error = str(exc)
            self._client = None
            print(f"Live telemetry: BigQuery unavailable ({exc}).")

    def observe(self, state: dict[str, Any], topic: str, payload: Any) -> list[dict[str, Any]]:
        if topic == "CarData.z":
            samples = car_samples(payload)
            kind = "car"
        elif topic == "Position.z":
            samples = position_samples(payload)
            kind = "pos"
        else:
            return []
        ready: list[dict[str, Any]] = []
        for sample in samples:
            ready.extend(self._absorb(state, kind, sample))
        if ready:
            self._queue(ready)
        return ready

    def _absorb(
        self, state: dict[str, Any], kind: str, sample: dict[str, Any]
    ) -> list[dict[str, Any]]:
        driver = sample["driver"]
        when: datetime = sample["at"]
        if kind == "car":
            self._car[driver] = sample
        else:
            self._pos[driver] = sample

        info = state.get("session_info") or {}
        identity = timing_state._session_identity(info)
        if not identity.get("session_key"):
            return []

        lap = _current_lap(state, driver)
        origin = self._origin.get(driver)
        if origin is None or origin[0] != lap:
            self._origin[driver] = (lap, when)
            self._next_t[driver] = 0.0
            self._prev_speed[driver] = None
            self._cumulative[driver] = 0.0
            origin = self._origin[driver]

        elapsed = (when - origin[1]).total_seconds()
        if elapsed < 0:
            elapsed = 0.0
        have_both = driver in self._car and driver in self._pos
        bucket = round(math.floor((elapsed + 1e-9) / INTERVAL_SEC) * INTERVAL_SEC, 1)
        if not have_both and elapsed < self._next_t.get(driver, 0.0) + 1.0:
            return []

        rows: list[dict[str, Any]] = []
        steps = 0
        while self._next_t[driver] <= bucket + 1e-9 and steps < MAX_CATCHUP:
            t = self._next_t[driver]
            row = self._row(identity, info, driver, lap, t, when)
            if row is not None:
                rows.append(row)
            self._next_t[driver] = round(t + INTERVAL_SEC, 1)
            steps += 1
        return rows

    def _row(
        self,
        identity: dict[str, Any],
        info: dict[str, Any],
        driver: str,
        lap: int,
        t: float,
        when: datetime,
    ) -> dict[str, Any] | None:
        car = self._car.get(driver)
        pos = self._pos.get(driver)
        if car is None and pos is None:
            return None
        speed = None if car is None else car.get("speed")
        previous = self._prev_speed.get(driver)
        if isinstance(speed, (int, float)) and isinstance(previous, (int, float)):
            deceleration = round((speed - previous) / INTERVAL_SEC, 2)
        else:
            deceleration = 0.0
        if isinstance(speed, (int, float)):
            distance = round((float(speed) / 3.6) * INTERVAL_SEC, 2)
            self._prev_speed[driver] = float(speed)
        else:
            distance = 0.0
        cumulative = round(self._cumulative.get(driver, 0.0) + distance, 2)
        self._cumulative[driver] = cumulative
        gear = None if car is None or car.get("gear") is None else int(car["gear"])
        drs = 0 if car is None or car.get("drs") is None else int(car["drs"])
        return {
            "session_key": identity.get("session_key"),
            "meeting_key": identity.get("meeting_key"),
            "season": identity.get("season"),
            "driver_number": driver,
            "lap_number": lap,
            "date": when.isoformat(),
            "lap_time_sec": t,
            "interval_sec": INTERVAL_SEC,
            "speed": None if speed is None else float(speed),
            "throttle": None if car is None or car.get("throttle") is None else float(car["throttle"]),
            "brake": None if car is None else car.get("brake"),
            "gear": gear,
            "rpm": None if car is None or car.get("rpm") is None else float(car["rpm"]),
            "drs": drs,
            "deceleration": deceleration,
            "distance_m": distance,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "session_type": identity.get("session_type"),
            "event_name": identity.get("event_name"),
            "circuit": _circuit(info),
            "x": None if pos is None else pos.get("x"),
            "y": None if pos is None else pos.get("y"),
            "z": None if pos is None else pos.get("z"),
            "cumulative_distance": cumulative,
        }

    def _point_id(self, row: dict[str, Any]) -> str:
        return (
            f"{row.get('session_key')}-{row.get('driver_number')}-"
            f"{row.get('lap_number')}-{float(row.get('lap_time_sec') or 0):.1f}"
        )

    def _append_local(self, rows: list[dict[str, Any]]) -> None:
        path = self.directory / "telemetry-live.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":"), default=str) + "\n")

    def _queue(self, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            for row in rows:
                key = self._point_id(row)
                if key in self._seen:
                    continue
                self._seen.add(key)
                self._pending.append(row)

    def flush(self) -> int:
        with self._lock:
            rows = self._pending
            self._pending = []
        if not rows:
            return 0
        if not self._bq_ready or self._client is None:
            self._append_local(rows)
            self.inserted += len(rows)
            return len(rows)
        written = 0
        for start in range(0, len(rows), 400):
            batch = rows[start : start + 400]
            ids = [self._point_id(row) for row in batch]
            try:
                errors = self._client.insert_rows_json(table_id(), batch, row_ids=ids)
            except Exception as exc:  # noqa: BLE001
                print(f"Live telemetry: insert failed ({exc}).")
                continue
            if errors:
                print(f"Live telemetry: insert errors: {errors[:2]}")
                continue
            written += len(batch)
        self.inserted += written
        if written:
            print(f"Live telemetry: inserted {written} row(s) into {table_id()}")
        return written

    @property
    def bigquery_ready(self) -> bool:
        return self._bq_ready

    @property
    def bigquery_error(self) -> str | None:
        return self._bq_error
