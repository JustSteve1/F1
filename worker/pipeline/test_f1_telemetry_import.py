"""FastF1 skip-existing includes sessions already stored in laps_live."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.modules.setdefault("fastf1", MagicMock())
sys.modules.setdefault("numpy", MagicMock())
sys.modules.setdefault("pandas", MagicMock())
sys.modules.setdefault("google.cloud.bigquery", MagicMock())
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.cloud", MagicMock())

import f1_telemetry_import as pipe  # noqa: E402


class _Row:
    def __init__(self, season: int, session_type: str):
        self._data = {"season": season, "session_type": session_type}

    def __getitem__(self, key: str):
        return self._data[key]


class _Frame:
    def __init__(self, rows: list[_Row]):
        self._rows = rows

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, row


class _Job:
    def __init__(self, rows: list[_Row]):
        self._rows = rows

    def to_dataframe(self):
        return _Frame(self._rows)


class _Client:
    def __init__(self, by_table: dict[str, list[_Row]]):
        self.by_table = by_table
        self.queries: list[str] = []

    def query(self, sql: str):
        self.queries.append(sql)
        for table, rows in self.by_table.items():
            if f".{table}`" in sql or f".{table} " in sql:
                return _Job(rows)
        raise RuntimeError(f"unexpected table in {sql}")


class LiveSkipTests(unittest.TestCase):
    def test_a_live_session_is_treated_as_already_present(self) -> None:
        client = _Client(
            {
                "telemetry": [_Row(2026, "FP1")],
                "laps_live": [_Row(2026, "Q")],
            }
        )
        found = pipe.check_existing(client, [2026], "United States Grand Prix", ["FP1", "Q", "R"])
        self.assertEqual(set(found), {(2026, "FP1"), (2026, "Q")})
        self.assertTrue(any("laps_live" in query for query in client.queries))

    def test_missing_live_table_does_not_block_the_batch_check(self) -> None:
        class BatchOnly(_Client):
            def query(self, sql: str):
                if "laps_live" in sql:
                    raise RuntimeError("laps_live is not there")
                return super().query(sql)

        client = BatchOnly({"telemetry": [_Row(2026, "R")]})
        found = pipe.check_existing(client, [2026], "United States Grand Prix", ["R"])
        self.assertEqual(set(found), {(2026, "R")})


if __name__ == "__main__":
    unittest.main()
