"""10 Hz telemetry from the livetiming car streams.

CarData.z and Position.z are the same hub as TimingData. Samples are kept
per car and, when a lap finishes, resampled onto a 0.1 second grid. Rows go
to telemetry_live. The Kaggle view reads that table for a live lap and does
not read the FastF1 telemetry table for it.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import archive_telemetry
import timing_state

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
TABLE = "telemetry_live"

# Native packets are about six a second. 0.1s is the resample, matching the
# warehouse. A grid point with no sample inside this window is left empty.
SAMPLE_SEC = 0.1
NEAREST_TOLERANCE_SEC = 0.2
# Safety-car laps can run long. Keep enough buffer to cover one of them.
BUFFER_SEC = 360


def table_id() -> str:
    return f"{PROJECT}.{DATASET}.{TABLE}"


def source_table_id() -> str:
    return f"{PROJECT}.{DATASET}.telemetry"


class CarBuffer:
    """Per-car car and position samples from the live feed."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cars: dict[str, list[tuple[datetime, dict[str, Any]]]] = {}
        self._positions: dict[str, list[tuple[datetime, dict[str, float]]]] = {}

    def add(self, topic: str, payload: Any) -> int:
        if topic == "CarData.z":
            samples = archive_telemetry.car_samples_from_payload(payload)
            target = self._cars
        elif topic == "Position.z":
            samples = archive_telemetry.position_samples_from_payload(payload)
            target = self._positions
        else:
            return 0
        if not samples:
            return 0
        with self._lock:
            for driver, instant, sample in samples:
                series = target.setdefault(driver, [])
                series.append((instant, sample))
            self._prune(samples[-1][1])
        return len(samples)

    def _prune(self, latest: datetime) -> None:
        cutoff = latest - timedelta(seconds=BUFFER_SEC)
        for series in (self._cars, self._positions):
            for driver, rows in list(series.items()):
                kept = [row for row in rows if row[0] >= cutoff]
                if kept:
                    series[driver] = kept
                else:
                    series.pop(driver, None)

    def resample(self, driver: str, ended_at: datetime, duration: float) -> list[dict[str, Any]]:
        """10 Hz points for the lap that ended at ended_at."""
        if duration <= 0:
            return []
        driver = str(driver)
        with self._lock:
            cars = list(self._cars.get(driver) or [])
            positions = list(self._positions.get(driver) or [])
        end = ended_at
        if cars:
            latest = cars[-1][0]
            if abs((latest - ended_at).total_seconds()) <= 2:
                end = latest
        start = end - timedelta(seconds=float(duration))
        window = {
            "driver_number": driver,
            "lap_number": 0,
            "start": start,
            "end": end,
        }
        return archive_telemetry.sample_lap(
            window,
            cars,
            positions,
            interval=SAMPLE_SEC,
            tolerance=NEAREST_TOLERANCE_SEC,
        )


class LiveTelemetryLog:
    """Insert one finished lap of 10 Hz samples into telemetry_live."""

    def __init__(self, *, bigquery: bool = True):
        self._seen: set[str] = set()
        self._lock = threading.Lock()
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

    def record(self, laps: list[dict[str, Any]], buffer: CarBuffer, ended_at: datetime) -> int:
        pending: list[dict[str, Any]] = []
        imported_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            for lap in laps:
                key = timing_state.lap_id(lap)
                if key in self._seen or lap.get("session_key") is None:
                    continue
                duration = lap.get("lap_duration")
                if not isinstance(duration, (int, float)) or duration <= 0:
                    continue
                points = buffer.resample(str(lap.get("driver_number")), ended_at, float(duration))
                if not points:
                    continue
                self._seen.add(key)
                for point in points:
                    point.update(
                        {
                            "session_key": lap.get("session_key"),
                            "meeting_key": lap.get("meeting_key"),
                            "season": lap.get("season"),
                            "event_name": lap.get("event_name"),
                            "session_type": lap.get("session_type"),
                            "circuit": lap.get("event_name"),
                            "lap_number": lap.get("lap_number"),
                            "imported_at": imported_at,
                        }
                    )
                    pending.append(point)
        if pending:
            self._insert(pending)
        return len(pending)

    def _insert(self, rows: list[dict[str, Any]]) -> None:
        if not self._bq_ready or self._client is None or not rows:
            return
        for start in range(0, len(rows), 500):
            batch = rows[start : start + 500]
            ids = [
                f"{row.get('session_key')}-{row.get('driver_number')}-"
                f"{row.get('lap_number')}-{row.get('lap_time_sec')}"
                for row in batch
            ]
            try:
                errors = self._client.insert_rows_json(table_id(), batch, row_ids=ids)
            except Exception as exc:  # noqa: BLE001
                print(f"Live telemetry: insert failed ({exc}).")
                return
            if errors:
                print(f"Live telemetry: insert errors: {errors[:2]}")
                return
        print(f"Live telemetry: inserted {len(rows)} sample(s) into {table_id()}")

    @property
    def bigquery_ready(self) -> bool:
        return self._bq_ready

    @property
    def bigquery_error(self) -> str | None:
        return self._bq_error
