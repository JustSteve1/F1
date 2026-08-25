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

    from ingest_source import assert_fastf1_ingest, ingest_source
    import db
    from job_runner import run

    print(f"INGEST_SOURCE={ingest_source()}", flush=True)
    try:
        assert_fastf1_ingest()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        try:
            db.update_job(
                job_id,
                status="failed",
                finished=True,
                error=str(exc),
                status_message="Unsupported ingest source",
            )
            db.append_log(job_id, str(exc), level="error")
        except Exception:
            pass
        return 2

    return run(job_id)


if __name__ == "__main__":
    raise SystemExit(main())
