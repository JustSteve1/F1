#!/usr/bin/env python3
"""Load FastF1 sessions locally and upload the cache to GCS for Cloud Run.

Example (Monaco 2026 Qualifying + Race):
    export FASTF1_CACHE_GCS_URI=gs://f1-data-library-fastf1-cache/fastf1
    python3 worker/pipeline/seed_fastf1_cache.py \
      --year 2026 --race "Monaco Grand Prix" --session Q R

Or with gsutil after a local load:
    gsutil -m rsync -r ~/.cache/fastf1 gs://f1-data-library-fastf1-cache/fastf1
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow importing sibling modules when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1  # noqa: E402
import fastf1_cache_sync  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed FastF1 cache to GCS")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--race", type=str, required=True)
    parser.add_argument(
        "--session",
        nargs="+",
        default=["Q"],
        help="Session codes, e.g. Q R FP1",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.environ.get(
            "FASTF1_CACHE_DIR", os.path.expanduser("~/.cache/fastf1")
        ),
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Only load locally; do not push to GCS",
    )
    args = parser.parse_args()

    cache_dir = args.cache_dir
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    print(f"Cache dir: {cache_dir}")

    for stype in args.session:
        print(f"Loading {args.year} {args.race} {stype}…")
        session = fastf1.get_session(args.year, args.race, stype)
        session.load(telemetry=True, laps=True, weather=False)
        print(
            f"  ✅  {stype}: {len(session.drivers)} drivers, "
            f"{len(session.laps)} laps"
        )

    if args.skip_upload:
        print("Skip upload (--skip-upload)")
        return 0

    uri = os.environ.get("FASTF1_CACHE_GCS_URI", "").strip()
    if not uri:
        print(
            "FASTF1_CACHE_GCS_URI unset. Set it or run:\n"
            f"  gsutil -m rsync -r {cache_dir} "
            "gs://f1-data-library-fastf1-cache/fastf1",
            file=sys.stderr,
        )
        return 1

    result = fastf1_cache_sync.push_cache(cache_dir, log=print)
    print(f"Done: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
