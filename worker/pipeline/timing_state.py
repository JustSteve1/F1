"""In-memory merge of F1 livetiming feed messages.

TimingData arrives as patches. A later sector update must keep the lap
time and position already stored for that driver.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_state() -> dict[str, Any]:
    return {
        "session_info": {},
        "session_status": None,
        "clock": {},
        "track_status": None,
        "lap_count": None,
        "lines": {},
        "drivers_meta": {},
    }


def _numeric_keys(value: dict) -> bool:
    return bool(value) and all(str(key).isdigit() for key in value)


def deep_merge(base: Any, patch: Any) -> Any:
    """Merge dict and indexed-list patches.

    Livetiming sends a sector list with lap times, then later sends a dict
    such as {"0": {"Segments": ...}}. Those have to combine, or the time is
    replaced by the segment patch.
    """
    if isinstance(base, dict) and isinstance(patch, dict):
        merged = dict(base)
        for key, value in patch.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    if isinstance(base, list) and isinstance(patch, list):
        merged = list(base)
        for index, value in enumerate(patch):
            if index < len(merged):
                merged[index] = deep_merge(merged[index], value)
            else:
                merged.append(value)
        return merged

    if isinstance(base, list) and isinstance(patch, dict) and _numeric_keys(patch):
        merged = list(base)
        for key, value in patch.items():
            index = int(key)
            while len(merged) <= index:
                merged.append({})
            merged[index] = deep_merge(merged[index], value)
        return merged

    if isinstance(base, dict) and isinstance(patch, list) and _numeric_keys(base):
        merged = dict(base)
        for index, value in enumerate(patch):
            key = str(index)
            merged[key] = deep_merge(merged.get(key), value)
        return merged

    return patch


def _value_of(node: Any) -> Any:
    if isinstance(node, dict) and "Value" in node:
        return node.get("Value")
    return node


def _sector(sectors: Any, index: int) -> Any:
    if isinstance(sectors, dict):
        node = sectors.get(str(index), sectors.get(index))
        return _value_of(node)
    if isinstance(sectors, list) and index < len(sectors):
        return _value_of(sectors[index])
    return None


def _line_status(line: dict[str, Any]) -> str:
    if line.get("Retired") is True:
        return "retired"
    if line.get("Stopped") is True:
        return "stopped"
    if line.get("InPit") is True:
        return "pit"
    if line.get("PitOut") is True:
        return "pit_out"
    if line.get("KnockedOut") is True:
        return "out"
    status = line.get("Status")
    if isinstance(status, str) and status:
        return status
    return "on_track"


def _timing_lines(payload: dict[str, Any]) -> dict[str, Any] | None:
    lines = payload.get("Lines")
    if isinstance(lines, dict):
        return lines
    return None


def apply_message(state: dict[str, Any], topic: str, payload: Any) -> None:
    if topic == "TimingData" and isinstance(payload, dict):
        lines = _timing_lines(payload)
        if lines is None:
            return
        for number, patch in lines.items():
            if not isinstance(patch, dict):
                continue
            key = str(number)
            state["lines"][key] = deep_merge(state["lines"].get(key, {}), patch)
        return

    if topic == "DriverList" and isinstance(payload, dict):
        for number, patch in payload.items():
            if not isinstance(patch, dict):
                continue
            key = str(number)
            state["drivers_meta"][key] = deep_merge(
                state["drivers_meta"].get(key, {}), patch
            )
        return

    if topic == "SessionInfo" and isinstance(payload, dict):
        state["session_info"] = deep_merge(state["session_info"], payload)
        return

    if topic == "SessionStatus":
        state["session_status"] = payload
        return

    if topic == "ExtrapolatedClock" and isinstance(payload, dict):
        state["clock"] = deep_merge(state["clock"], payload)
        return

    if topic == "TrackStatus":
        state["track_status"] = payload
        return

    if topic == "LapCount":
        state["lap_count"] = payload
        return


def _position_key(row: dict[str, Any]) -> tuple[int, int]:
    try:
        position = int(row["position"])
    except (TypeError, ValueError):
        position = 10_000
    try:
        number = int(row["driver_number"])
    except (TypeError, ValueError):
        number = 10_000
    return position, number


def _session_view(state: dict[str, Any]) -> dict[str, Any]:
    info = state.get("session_info") or {}
    meeting = info.get("Meeting") if isinstance(info.get("Meeting"), dict) else {}
    status = state.get("session_status")
    status_name = status.get("Status") if isinstance(status, dict) else status
    return {
        "name": info.get("Name") or meeting.get("Name"),
        "type": info.get("Type"),
        "meeting": meeting.get("OfficialName") or meeting.get("Name"),
        "path": info.get("Path"),
        "status": status_name,
    }


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    drivers: list[dict[str, Any]] = []
    numbers = set(state["lines"]) | set(state["drivers_meta"])
    for number in numbers:
        line = state["lines"].get(number) or {}
        meta = state["drivers_meta"].get(number) or {}
        if not line and not meta:
            continue
        drivers.append(
            {
                "driver_number": str(number),
                "tla": meta.get("Tla") or meta.get("BroadcastName"),
                "position": line.get("Position"),
                "gap": _value_of(line.get("GapToLeader")),
                "interval": _value_of(line.get("IntervalToPositionAhead")),
                "last_lap": _value_of(line.get("LastLapTime")),
                "sector1": _sector(line.get("Sectors"), 0),
                "sector2": _sector(line.get("Sectors"), 1),
                "sector3": _sector(line.get("Sectors"), 2),
                "status": _line_status(line) if line else None,
            }
        )
    drivers.sort(key=_position_key)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "session": _session_view(state),
        "clock": state.get("clock") or {},
        "track_status": state.get("track_status"),
        "lap_count": state.get("lap_count"),
        "drivers": drivers,
    }


def replay_jsonl(path: Path | str) -> dict[str, Any]:
    """Rebuild a snapshot from an archive written by the subscriber."""
    state = new_state()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            apply_message(state, record.get("topic"), record.get("payload"))
    return snapshot(state)
