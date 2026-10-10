"""Combine a Kaggle CSV with rows from the laps_kaggle view.

A view row replaces a Kaggle row with the same lap. Rows that exist only
on Kaggle stay. The view already prefers the batch laps table over laps_live,
so this is how a later batch load corrects a lap that was published live.
"""

from __future__ import annotations

from typing import Any

KAGGLE_COLUMNS = (
    "season",
    "event_name",
    "circuit",
    "session_type",
    "driver",
    "driver_number",
    "lap_number",
    "lap_time",
    "lap_duration",
    "compound",
    "tyre_age",
    "stint_number",
    "telemetry",
)

LAP_KEY = ("season", "event_name", "session_type", "driver_number", "lap_number")


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def lap_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _number(row.get("season")),
        str(row.get("event_name")),
        str(row.get("session_type")),
        _number(row.get("driver_number")),
        _number(row.get("lap_number")),
    )


def _project(row: dict[str, Any]) -> dict[str, Any]:
    return {column: row.get(column) for column in KAGGLE_COLUMNS}


def combine_kaggle_rows(
    existing: list[dict[str, Any]],
    view_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """View rows win. Kaggle rows whose lap is not in the view are kept."""
    view = [_project(row) for row in view_rows]
    view_keys = {lap_key(row) for row in view}
    kept = [_project(row) for row in existing if lap_key(row) not in view_keys]
    combined = kept + view
    combined.sort(key=lap_key)
    return combined


_NUMERIC = {"season", "driver_number", "lap_number", "lap_duration", "tyre_age", "stint_number"}


def _cell(column: str, value: Any) -> Any:
    if column in _NUMERIC:
        return _number(value)
    if value is None:
        return None
    return value


def rows_unchanged(
    existing: list[dict[str, Any]],
    combined: list[dict[str, Any]],
) -> bool:
    def signature(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [
            tuple(_cell(column, row.get(column)) for column in KAGGLE_COLUMNS)
            for row in sorted((_project(row) for row in rows), key=lap_key)
        ]

    return signature(existing) == signature(combined)
