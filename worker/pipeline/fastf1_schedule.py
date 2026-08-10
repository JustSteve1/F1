#!/usr/bin/env python3
"""Export FastF1 event schedule as JSON for the admin import catalog.

Usage:
    python3 worker/pipeline/fastf1_schedule.py --year 2026
    python3 worker/pipeline/fastf1_schedule.py --year 2026 --race "Monaco Grand Prix"
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import pandas as pd

# Map schedule session display names → worker/FastF1 short codes
SESSION_NAME_TO_CODE = {
    "practice 1": "FP1",
    "practice 2": "FP2",
    "practice 3": "FP3",
    "qualifying": "Q",
    "sprint qualifying": "SQ",
    "sprint shootout": "SQ",
    "sprint": "S",
    "race": "R",
}


def _iso(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    ts = pd.Timestamp(val)
    if pd.isna(ts):
        return None
    return ts.isoformat()


def _session_code(label: Any) -> str | None:
    if label is None or (isinstance(label, float) and pd.isna(label)):
        return None
    text = str(label).strip()
    if not text or text.lower() == "nan":
        return None
    return SESSION_NAME_TO_CODE.get(text.lower())


def build_schedule(year: int, race: str | None = None) -> dict:
    import fastf1

    schedule = fastf1.get_event_schedule(year, include_testing=False)
    events = []

    for _, row in schedule.iterrows():
        event_name = str(row.get("EventName", "")).strip()
        if not event_name:
            continue
        if race and event_name.lower() != race.strip().lower():
            continue

        sessions = []
        for i in range(1, 6):
            label = row.get(f"Session{i}")
            code = _session_code(label)
            if not code:
                continue
            date_utc = _iso(row.get(f"Session{i}DateUtc"))
            sessions.append(
                {
                    "code": code,
                    "label": str(label).strip(),
                    "dateUtc": date_utc,
                }
            )

        # Deduplicate codes while preserving order (defensive)
        seen = set()
        unique_sessions = []
        for s in sessions:
            if s["code"] in seen:
                continue
            seen.add(s["code"])
            unique_sessions.append(s)

        events.append(
            {
                "eventName": event_name,
                "round": int(row["RoundNumber"]) if pd.notna(row.get("RoundNumber")) else None,
                "eventFormat": (
                    str(row["EventFormat"]) if pd.notna(row.get("EventFormat")) else None
                ),
                "location": (
                    str(row["Location"]) if pd.notna(row.get("Location")) else None
                ),
                "country": (
                    str(row["Country"]) if pd.notna(row.get("Country")) else None
                ),
                "sessions": unique_sessions,
            }
        )

    return {"year": year, "events": events}


def main() -> int:
    parser = argparse.ArgumentParser(description="Export FastF1 schedule JSON")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--race", type=str, default=None)
    args = parser.parse_args()

    try:
        payload = build_schedule(args.year, args.race)
    except Exception as e:
        print(
            json.dumps({"error": f"{type(e).__name__}: {e}", "year": args.year}),
            file=sys.stderr,
        )
        return 1

    if args.race and not payload["events"]:
        print(
            json.dumps(
                {
                    "error": f'Race "{args.race}" not found in {args.year} schedule',
                    "year": args.year,
                }
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
