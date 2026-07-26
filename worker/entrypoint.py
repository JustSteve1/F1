#!/usr/bin/env python3
"""Cloud Run Jobs entrypoint — expects JOB_ID in the environment."""

from __future__ import annotations

import os
import sys


def main() -> int:
    job_id = os.environ.get("JOB_ID")
    if not job_id:
        print("JOB_ID env var is required", file=sys.stderr)
        return 2

    # Allow importing sibling modules when run as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from job_runner import run

    return run(job_id)


if __name__ == "__main__":
    raise SystemExit(main())
