"""In-memory merge of F1 livetiming feed messages.

TimingData arrives as patches. A later sector update must keep the lap
time and position already stored for that driver.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Same columns as the batch `laps` insert in f1_telemetry_import.py.
LAP_COLUMNS = (
    "session_key",
    "meeting_key",
    "season",
    "event_name",
    "session_type",
    "driver_number",
    "driver_code",
    "team",
    "position",
    "lap_number",
    "lap_duration",
    "lap_start_time",
    "sector_1_time",
    "sector_2_time",
    "sector_3_time",
    "sector_1_session_time",
    "sector_2_session_time",
    "sector_3_session_time",
    "pit_out_time",
    "pit_in_time",
    "speed_i1",
    "speed_i2",
    "speed_st",
    "compound",
    "tyre_age_laps",
    "stint_number",
    "fresh_tyre",
    "is_accurate",
    "is_personal_best",
    "deleted",
    "deleted_reason",
    "fastf1_generated",
    "track_status",
    "lap_start_date",
    "imported_at",
)


def new_state() -> dict[str, Any]:
    return {
        "session_info": {},
        "session_status": None,
        "clock": {},
        "track_status": None,
        "lap_count": None,
        "lines": {},
        "drivers_meta": {},
        "timing_app": {},
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

    if topic == "TimingAppData" and isinstance(payload, dict):
        lines = _timing_lines(payload)
        if lines is None:
            return
        for number, patch in lines.items():
            if not isinstance(patch, dict):
                continue
            key = str(number)
            state["timing_app"][key] = deep_merge(state["timing_app"].get(key, {}), patch)
        return


def _parse_clock(value: Any) -> float | None:
    """Parse a livetiming clock. '1:32.100' is 92.1 seconds. A bare number is seconds."""
    if isinstance(value, dict):
        if "Value" not in value:
            return None
        value = value.get("Value")
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 1:
            number = float(parts[0])
        elif len(parts) == 2:
            number = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            number = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            return None
    except ValueError:
        return None
    return number if number > 0 else None


def _lap_count(line: dict[str, Any]) -> int | None:
    raw = line.get("NumberOfLaps")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return None


def _sector_seconds(sectors: Any, index: int) -> float | None:
    return _parse_clock(_sector(sectors, index))


def _chosen_sector(previous: Any, patch: Any, index: int) -> float | None:
    """Prefer a real time on the completing patch, otherwise the time already stored.

    A completing TimingData message often replaces sector times with a segment
    dict and no Value. That must not wipe the time recorded on the lap.
    """
    if patch is not None:
        patched = _sector_seconds(patch, index)
        if patched is not None:
            return patched
    return _sector_seconds(previous, index)


def _speed(line: dict[str, Any], name: str) -> float | None:
    speeds = line.get("Speeds")
    if not isinstance(speeds, dict):
        return None
    return _parse_clock(speeds.get(name))


def _chosen_speed(previous: dict[str, Any], patch: dict[str, Any], name: str) -> float | None:
    patched = _speed(patch, name)
    if patched is not None:
        return patched
    return _speed(previous, name)


def _last_stint(app: dict[str, Any]) -> tuple[dict[str, Any] | None, int | None]:
    stints = app.get("Stints")
    if isinstance(stints, list) and stints:
        current = stints[-1]
        if isinstance(current, dict):
            return current, len(stints)
        return None, None
    if isinstance(stints, dict) and _numeric_keys(stints):
        index = max(int(key) for key in stints)
        current = stints.get(str(index), stints.get(index))
        if isinstance(current, dict):
            return current, index + 1
    return None, None


def _session_identity(info: dict[str, Any]) -> dict[str, Any]:
    meeting = info.get("Meeting") if isinstance(info.get("Meeting"), dict) else {}
    event_name = meeting.get("Name") or meeting.get("OfficialName")
    year = None
    for source in (
        info.get("Path"),
        info.get("StartDate"),
        meeting.get("Date"),
    ):
        if isinstance(source, str):
            match = re.search(r"(20\d{2})", source)
            if match:
                year = int(match.group(1))
                break
    session_type = _session_type_code(info.get("Name"), info.get("Type"))
    session_key = None
    if year is not None and event_name and session_type:
        key_str = f"{year}-{event_name}-{session_type}"
        session_key = int(hashlib.md5(key_str.encode()).hexdigest()[:8], 16)
    return {
        "session_key": session_key,
        "meeting_key": session_key,
        "season": year,
        "event_name": event_name,
        "session_type": session_type,
    }


def _session_type_code(name: Any, kind: Any) -> str | None:
    text = " ".join(str(part) for part in (name, kind) if part).lower()
    if not text:
        return None
    if "practice 1" in text or text.strip() in {"fp1", "p1"}:
        return "FP1"
    if "practice 2" in text or text.strip() in {"fp2", "p2"}:
        return "FP2"
    if "practice 3" in text or text.strip() in {"fp3", "p3"}:
        return "FP3"
    if "sprint qualifying" in text or "sprint shootout" in text:
        return "SQ"
    if "sprint" in text:
        return "S"
    if "qualifying" in text:
        return "Q"
    if "race" in text:
        return "R"
    return None


def _track_code(track_status: Any) -> str | None:
    if isinstance(track_status, dict):
        status = track_status.get("Status")
        if status is not None and str(status).strip():
            return str(status)
        message = track_status.get("Message")
        if isinstance(message, str) and message.strip():
            return message.strip()
        return None
    if isinstance(track_status, str) and track_status.strip():
        return track_status.strip()
    return None


def lap_id(row: dict[str, Any]) -> str:
    return f"{row.get('session_key')}-{row.get('driver_number')}-{row.get('lap_number')}"


def completed_lap_rows(state: dict[str, Any], topic: str, payload: Any) -> list[dict[str, Any]]:
    """Return laps finished by this payload. Call before apply_message.

    NumberOfLaps is the count of laps already finished. One row is emitted
    for the new count when that count increases and LastLapTime is a real time.
    A jump of more than one lap still emits only the latest completed lap.
    """
    if topic != "TimingData" or not isinstance(payload, dict):
        return []
    lines = _timing_lines(payload)
    if lines is None:
        return []
    identity = _session_identity(state.get("session_info") or {})
    track = _track_code(state.get("track_status"))
    imported_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for number, patch in lines.items():
        if not isinstance(patch, dict) or "NumberOfLaps" not in patch:
            continue
        new_count = _lap_count(patch)
        if new_count is None or new_count < 1:
            continue
        key = str(number)
        previous = state["lines"].get(key) or {}
        old_count = _lap_count(previous) or 0
        if new_count <= old_count:
            continue
        duration = _parse_clock(patch.get("LastLapTime"))
        if duration is None:
            continue
        last_lap = patch.get("LastLapTime")
        personal = last_lap.get("PersonalFastest") if isinstance(last_lap, dict) else None
        meta = state["drivers_meta"].get(key) or {}
        app = state["timing_app"].get(key) or {}
        stint, stint_number = _last_stint(app)
        stint = stint or {}
        sector_1 = _chosen_sector(previous.get("Sectors"), patch.get("Sectors"), 0)
        sector_2 = _chosen_sector(previous.get("Sectors"), patch.get("Sectors"), 1)
        sector_3 = _chosen_sector(previous.get("Sectors"), patch.get("Sectors"), 2)
        row = {column: None for column in LAP_COLUMNS}
        row.update(identity)
        row.update(
            {
                "driver_number": key,
                "driver_code": meta.get("Tla") or meta.get("BroadcastName"),
                "team": meta.get("TeamName") or meta.get("Team"),
                "position": _int_or_none(patch.get("Position", previous.get("Position"))),
                "lap_number": new_count,
                "lap_duration": duration,
                "sector_1_time": sector_1,
                "sector_2_time": sector_2,
                "sector_3_time": sector_3,
                "speed_i1": _chosen_speed(previous, patch, "I1"),
                "speed_i2": _chosen_speed(previous, patch, "I2"),
                "speed_st": _chosen_speed(previous, patch, "ST"),
                "compound": stint.get("Compound"),
                "tyre_age_laps": _int_or_none(stint.get("TotalLaps")),
                "stint_number": stint_number,
                "fresh_tyre": _bool_or_none(stint.get("New")),
                "is_personal_best": _bool_or_none(personal),
                "track_status": track,
                "imported_at": imported_at,
            }
        )
        rows.append(row)
    return rows


def replay_laps(path: Path | str) -> list[dict[str, Any]]:
    """Rebuild completed laps from an archive. Newest lap is first."""
    state = new_state()
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            topic = record.get("topic")
            payload = record.get("payload")
            for row in completed_lap_rows(state, topic, payload):
                key = lap_id(row)
                if key in seen:
                    continue
                seen.add(key)
                found.append(row)
            apply_message(state, topic, payload)
    found.reverse()
    return found


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
