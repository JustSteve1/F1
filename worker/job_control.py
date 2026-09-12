"""Pure job-control helpers (no Postgres)."""

from __future__ import annotations


def desired_status_on_stop(current: str) -> str | None:
    """What Postgres status to write when Cloud Run sends SIGTERM/SIGINT."""
    if current in ("succeeded", "failed", "cancelled"):
        return None
    if current == "cancelling":
        return "cancelled"
    return "failed"


def status_guard_sql(status: str | None) -> str:
    """Do not let a dying worker overwrite admin cancel / force-fail / success."""
    if status is None:
        return ""
    if status in ("succeeded", "running", "queued"):
        return " AND status NOT IN ('failed', 'cancelled', 'succeeded')"
    if status == "cancelling":
        return " AND status IN ('queued', 'running')"
    if status == "cancelled":
        return " AND status IN ('queued', 'running', 'cancelling')"
    if status == "failed":
        return " AND status IN ('queued', 'running', 'cancelling')"
    return ""
