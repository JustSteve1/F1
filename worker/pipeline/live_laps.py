"""Append completed live laps to a local file and to BigQuery laps_live.

The batch importer keeps writing `laps`. This module never touches that table.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

import timing_state

PROJECT = os.environ.get("BQ_PROJECT", "f1-data-library")
DATASET = os.environ.get("BQ_DATASET", "f1_data_library_DS")
TABLE = "laps_live"


def table_id() -> str:
    return f"{PROJECT}.{DATASET}.{TABLE}"


def source_table_id() -> str:
    return f"{PROJECT}.{DATASET}.laps"


class LapLog:
    def __init__(self, directory: Path, *, bigquery: bool = True):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "live-laps.json"
        self._lock = threading.Lock()
        self._rows: list[dict[str, Any]] = []
        self._seen: set[str] = set()
        self._bq_ready = False
        self._bq_error: str | None = None
        self._client: Any = None
        self._load()
        if bigquery:
            self._prepare_bigquery()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        rows = payload.get("laps") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return
        self._rows = [row for row in rows if isinstance(row, dict)]
        self._seen = {timing_state.lap_id(row) for row in self._rows}

    def _write(self) -> None:
        text = json.dumps({"laps": self._rows}, indent=2, default=str)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)

    def _prepare_bigquery(self) -> None:
        try:
            from google.cloud import bigquery
        except ImportError:
            self._bq_error = "google-cloud-bigquery is not installed"
            print(f"Live laps: {self._bq_error}. Writing {self.path.name} only.")
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
            print(f"Live laps: BigQuery unavailable ({exc}). Writing {self.path.name} only.")
            return
        self._sync_missing()

    def remember(self, lap_ids: set[str]) -> None:
        """Treat these lap ids as already stored so a later add does not insert them."""
        self._seen.update(lap_ids)

    def skip_stored(self) -> int:
        """Load recent BigQuery lap ids. Raises if the lookup fails."""
        if not self._bq_ready or self._client is None:
            raise RuntimeError("BigQuery is not ready; refusing to write laps without a duplicate check")
        query = f"""
            SELECT CONCAT(
                CAST(session_key AS STRING), '-',
                driver_number, '-',
                CAST(lap_number AS STRING)
            ) AS lap_id
            FROM `{table_id()}`
            WHERE imported_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
        """
        try:
            found = {row.lap_id for row in self._client.query(query).result()}
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"could not read existing lap ids: {exc}") from exc
        self.remember(found)
        return len(found)

    def _remote_ids(self) -> set[str]:
        if not self._bq_ready or self._client is None:
            return set()
        query = f"""
            SELECT CONCAT(
                CAST(session_key AS STRING), '-',
                driver_number, '-',
                CAST(lap_number AS STRING)
            ) AS lap_id
            FROM `{table_id()}`
            WHERE imported_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
        """
        try:
            return {row.lap_id for row in self._client.query(query).result()}
        except Exception as exc:  # noqa: BLE001
            print(f"Live laps: could not read existing ids ({exc}).")
            return set()

    def _sync_missing(self) -> None:
        remote = self._remote_ids()
        pending = [
            row for row in reversed(self._rows) if timing_state.lap_id(row) not in remote
        ]
        if pending:
            self._insert(pending)

    def _insert(self, rows: list[dict[str, Any]]) -> None:
        if not self._bq_ready or self._client is None or not rows:
            return
        ids = [timing_state.lap_id(row) for row in rows]
        try:
            errors = self._client.insert_rows_json(table_id(), rows, row_ids=ids)
        except Exception as exc:  # noqa: BLE001
            print(f"Live laps: insert failed ({exc}).")
            return
        if errors:
            print(f"Live laps: insert errors: {errors[:2]}")
            return
        print(f"Live laps: inserted {len(rows)} row(s) into {table_id()}")

    def add(self, rows: list[dict[str, Any]]) -> int:
        fresh: list[dict[str, Any]] = []
        with self._lock:
            for row in rows:
                key = timing_state.lap_id(row)
                if key in self._seen:
                    continue
                self._seen.add(key)
                self._rows.insert(0, row)
                fresh.append(row)
            if fresh:
                self._write()
        if fresh:
            self._insert(fresh)
        return len(fresh)

    @property
    def bigquery_ready(self) -> bool:
        return self._bq_ready

    @property
    def bigquery_error(self) -> str | None:
        return self._bq_error
