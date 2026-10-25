"""Start the live import for each session on the calendar, then stop it.

Runs on the home machine next to the subscriber. Every few minutes it:

1. reads the FastF1 event schedule (cached a day in the live directory),
2. keeps the subscription bearer fresh with ``live_token.ensure``,
3. starts ``live_subscriber.py`` ``--lead-minutes`` before a session,
4. restarts it if the hub drops the socket, and
5. stops it once ``SessionStatus`` says the session is over, or at the
   hard end of the window.

Everything it does is posted through ``notify`` and summarised in
``watcher-status.json`` for the ``/live`` page. Refuses to run on Cloud Run
for the same reason the subscriber does.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import f1_account  # noqa: E402
import live_token  # noqa: E402
import notify  # noqa: E402

HERE = Path(__file__).resolve().parent
SUBSCRIBER = HERE / "live_subscriber.py"

# Nominal running time per session code. The watcher stops earlier when the
# hub reports the session finished, and later only up to the grace period.
SESSION_LENGTH_MINUTES = {
    "FP1": 60,
    "FP2": 60,
    "FP3": 60,
    "SQ": 45,
    "S": 60,
    "Q": 60,
    "R": 180,
}
DEFAULT_LENGTH_MINUTES = 90
FINISHED_STATUSES = {"Finished", "Finalised", "Ends"}

STATUS_FILE = "watcher-status.json"
STATE_FILE = "watcher-state.json"
SUBSCRIBER_LOG = "watcher-subscriber.log"


def live_dir() -> Path:
    return notify.live_dir()


def assert_not_cloud_run() -> None:
    if os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_JOB"):
        raise RuntimeError(
            "Refusing to start on Cloud Run. Livetiming blocks datacenter IPs; "
            "run the watcher on a home or residential connection."
        )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _when(stamp: datetime) -> str:
    local = stamp.astimezone()
    return f"{stamp.strftime('%a %d %b %H:%M UTC')} ({local.strftime('%H:%M %Z')})"


# ── schedule ──────────────────────────────────────────────────────────────────


def schedule_path(year: int, directory: Path) -> Path:
    return directory / f"schedule-{year}.json"


def load_schedule(
    year: int,
    directory: Path,
    *,
    max_age: timedelta = timedelta(hours=24),
    refresh: bool = False,
) -> dict[str, Any]:
    """FastF1 schedule for ``year``, cached in the live directory.

    A stale cache is still used when FastF1 cannot be reached, so a flaky
    connection at T-60 does not lose the session.
    """
    cache = schedule_path(year, directory)
    cached: dict[str, Any] | None = None
    if cache.is_file():
        try:
            cached = json.loads(cache.read_text())
        except ValueError:
            cached = None
        if cached is not None and not refresh:
            age = utcnow() - datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc)
            if age <= max_age:
                return cached
    try:
        import fastf1_schedule

        fresh = fastf1_schedule.build_schedule(year)
    except Exception as exc:  # noqa: BLE001 — fall back to the cache
        if cached is not None:
            print(f"Schedule refresh failed ({exc}); using cached {cache}", file=sys.stderr)
            return cached
        raise RuntimeError(f"Could not load the {year} schedule: {exc}") from exc
    directory.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(fresh, indent=2))
    return fresh


@dataclass(frozen=True)
class SessionWindow:
    event: str
    round: int | None
    code: str
    label: str
    starts_at: datetime
    record_from: datetime
    record_until: datetime

    @property
    def key(self) -> str:
        return f"{self.starts_at.year}:{self.event}:{self.code}"

    def contains(self, now: datetime) -> bool:
        return self.record_from <= now < self.record_until

    def as_json(self) -> dict[str, Any]:
        data = asdict(self)
        for name in ("starts_at", "record_from", "record_until"):
            data[name] = getattr(self, name).isoformat()
        data["key"] = self.key
        return data


def session_windows(
    schedule: dict[str, Any],
    *,
    lead: timedelta,
    grace: timedelta,
    now: datetime | None = None,
) -> list[SessionWindow]:
    """Recording windows for every session that has not already closed."""
    now = now or utcnow()
    windows: list[SessionWindow] = []
    for event in schedule.get("events") or []:
        name = str(event.get("eventName") or "").strip()
        for session in event.get("sessions") or []:
            code = session.get("code")
            date = session.get("dateUtc")
            if not name or not code or not date:
                continue
            starts_at = _parse_iso(date)
            length = timedelta(minutes=SESSION_LENGTH_MINUTES.get(code, DEFAULT_LENGTH_MINUTES))
            window = SessionWindow(
                event=name,
                round=event.get("round"),
                code=code,
                label=str(session.get("label") or code),
                starts_at=starts_at,
                record_from=starts_at - lead,
                record_until=starts_at + length + grace,
            )
            if window.record_until > now:
                windows.append(window)
    windows.sort(key=lambda window: window.starts_at)
    return windows


def current_or_next(windows: list[SessionWindow], now: datetime, done: set[str]) -> SessionWindow | None:
    for window in windows:
        if window.key in done:
            continue
        if window.record_until > now:
            return window
    return None


# ── persisted state and status ────────────────────────────────────────────────


def load_state(directory: Path) -> dict[str, Any]:
    try:
        return json.loads((directory / STATE_FILE).read_text())
    except (OSError, ValueError):
        return {"recorded": []}


def save_state(directory: Path, state: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / STATE_FILE
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2, default=str))
    temporary.replace(path)


def write_status(directory: Path, **fields: Any) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    record = {"updated_at": utcnow().isoformat(), **fields}
    path = directory / STATUS_FILE
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2, default=str))
    temporary.replace(path)


def snapshot_status(directory: Path, since: datetime) -> str | None:
    """Session status from the subscriber's snapshot, if written after ``since``."""
    try:
        snap = json.loads((directory / "timing-snapshot.json").read_text())
    except (OSError, ValueError):
        return None
    updated = snap.get("updated_at")
    if not isinstance(updated, str):
        return None
    try:
        if _parse_iso(updated) < since:
            return None
    except ValueError:
        return None
    session = snap.get("session") or {}
    status = session.get("status")
    return status if isinstance(status, str) else None


def completed_laps(directory: Path) -> int:
    try:
        data = json.loads((directory / "live-laps.json").read_text())
    except (OSError, ValueError):
        return 0
    laps = data.get("laps") if isinstance(data, dict) else None
    return len(laps) if isinstance(laps, list) else 0


# ── token hygiene ─────────────────────────────────────────────────────────────


class TokenKeeper:
    """Runs ``live_token.ensure`` and reports only changes, not every check."""

    def __init__(self, directory: Path, *, allow_login: bool = True):
        self.directory = directory
        self.allow_login = allow_login
        self._last_alert: str | None = None
        self.last_record: dict[str, Any] | None = None

    def ensure(self) -> bool:
        """True when a usable token is on disk afterwards."""
        try:
            path, claims, action = live_token.ensure(allow_login=self.allow_login)
        except live_token.SignInRequired as exc:
            self._alert("sign_in_required", "Sign-in required for the live import", str(exc), "error")
            self.last_record = live_token.read_status()
            return False
        except f1_account.TemporaryFailure as exc:
            self._alert("temporary", "Token renewal hit a temporary failure", str(exc), "warning")
            self.last_record = live_token.read_status()
            return live_token.is_usable(self._stored_claims() or {})
        except Exception as exc:  # noqa: BLE001 — verification or IO problem
            self._alert("error", "Token check failed", str(exc), "error")
            return False

        self.last_record = live_token.read_status()
        expiry = live_token.time_left(claims)
        hours = f"{expiry.total_seconds() / 3600:.1f} h" if expiry else "unknown"
        if action == "renewed":
            self._alert(f"renewed:{claims.get('exp')}", "Subscription token renewed", f"Valid for another {hours}.")
        elif action == "signed_in":
            self._alert(f"signed_in:{claims.get('exp')}", "Signed in to the F1 account", f"New token valid for {hours}.")
        elif action == "kept_expiring":
            reason = (self.last_record or {}).get("error") or "no renewal path"
            self._alert(
                f"expiring:{claims.get('exp')}",
                "Subscription token could not be renewed",
                f"It still works for {hours}. {reason}",
                "warning",
            )
        else:
            self._last_alert = None
        return True

    def _stored_claims(self) -> dict[str, Any] | None:
        try:
            token = live_token.token_path().read_text().strip()
            return f1_account.claims(token) if token else None
        except (OSError, Exception):  # noqa: BLE001
            return None

    def _alert(self, key: str, title: str, message: str, level: str = "info") -> None:
        if self._last_alert == key:
            return
        self._last_alert = key
        notify.notify(title, message, level=level, directory=self.directory)


# ── recorder ──────────────────────────────────────────────────────────────────


class Recorder:
    def __init__(self, directory: Path, extra_args: list[str] | None = None):
        self.directory = directory
        self.extra_args = extra_args or []
        self.process: subprocess.Popen | None = None
        self.started_at: datetime | None = None
        self.restarts = 0

    def start(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        log = (self.directory / SUBSCRIBER_LOG).open("a", encoding="utf-8")
        log.write(f"\n--- watcher start {utcnow().isoformat()} ---\n")
        log.flush()
        self.process = subprocess.Popen(
            [sys.executable, "-u", str(SUBSCRIBER), "--dir", str(self.directory), *self.extra_args],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(HERE),
        )
        self.started_at = utcnow()

    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def exit_code(self) -> int | None:
        return None if self.process is None else self.process.poll()

    def stop(self, timeout: float = 45) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        # SIGINT lets the subscriber flush telemetry and print its topic rates.
        self.process.send_signal(signal.SIGINT)
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.process else None


# ── watcher ───────────────────────────────────────────────────────────────────


@dataclass
class Settings:
    directory: Path
    lead: timedelta
    grace: timedelta
    finalised: timedelta
    poll_seconds: int
    token_check: timedelta
    max_restarts: int
    allow_login: bool
    year: int | None = None


class Watcher:
    def __init__(self, settings: Settings):
        self.s = settings
        self.state = load_state(settings.directory)
        self.done: set[str] = set(self.state.get("recorded") or [])
        self.tokens = TokenKeeper(settings.directory, allow_login=settings.allow_login)
        self._last_token_check: datetime | None = None
        self._stop = False
        signal.signal(signal.SIGTERM, self._on_signal)

    def _on_signal(self, *_: Any) -> None:
        self._stop = True

    def windows(self, now: datetime) -> list[SessionWindow]:
        year = self.s.year or now.year
        schedule = load_schedule(year, self.s.directory)
        windows = session_windows(schedule, lead=self.s.lead, grace=self.s.grace, now=now)
        if not windows and self.s.year is None and now.month >= 11:
            try:
                later = load_schedule(year + 1, self.s.directory)
                windows = session_windows(later, lead=self.s.lead, grace=self.s.grace, now=now)
            except RuntimeError:
                pass
        return windows

    def _token_due(self, now: datetime, target: SessionWindow | None) -> bool:
        if self._last_token_check is None:
            return True
        if now - self._last_token_check >= self.s.token_check:
            return True
        if target is not None:
            pre_session = target.record_from - timedelta(minutes=15)
            if pre_session <= now and self._last_token_check < pre_session:
                return True
        return False

    def run(self) -> int:
        assert_not_cloud_run()
        notify.notify(
            "Watcher started",
            f"Recording from {int(self.s.lead.total_seconds() // 60)} min before each session; "
            f"archive in {self.s.directory}.",
            directory=self.s.directory,
        )
        while not self._stop:
            now = utcnow()
            try:
                windows = self.windows(now)
            except RuntimeError as exc:
                notify.notify("Schedule unavailable", str(exc), level="warning", directory=self.s.directory)
                write_status(self.s.directory, state="error", error=str(exc), token=self.tokens.last_record)
                self._sleep(600)
                continue

            target = current_or_next(windows, now, self.done)
            if target is None:
                write_status(self.s.directory, state="idle", next_session=None, token=self.tokens.last_record)
                self._sleep(3600)
                continue

            if self._token_due(now, target):
                self.tokens.ensure()
                self._last_token_check = now

            if now < target.record_from:
                write_status(
                    self.s.directory,
                    state="armed",
                    next_session=target.as_json(),
                    token=self.tokens.last_record,
                    upcoming=[window.as_json() for window in windows[:5]],
                )
                self._sleep(min((target.record_from - now).total_seconds(), 300))
                continue

            self.record(target)

        write_status(self.s.directory, state="stopped", token=self.tokens.last_record)
        notify.notify("Watcher stopped", directory=self.s.directory)
        return 0

    def record(self, window: SessionWindow) -> None:
        directory = self.s.directory
        # Wait for a usable token, but not past the end of the window.
        while not self._stop and utcnow() < window.record_until:
            if self.tokens.ensure():
                break
            write_status(
                directory,
                state="waiting_for_sign_in",
                next_session=window.as_json(),
                token=self.tokens.last_record,
            )
            self._sleep(min(300, (window.record_until - utcnow()).total_seconds()))
        if self._stop or utcnow() >= window.record_until:
            notify.notify(
                "Session missed",
                f"{window.event} {window.label}: no usable subscription token before the window closed.",
                level="error",
                directory=directory,
            )
            self._finish(window)
            return

        recorder = Recorder(directory)
        laps_before = completed_laps(directory)
        recorder.start()
        notify.notify(
            "Recording started",
            f"{window.event} {window.label} starts {_when(window.starts_at)}. "
            f"Recording until the session ends (hard stop {_when(window.record_until)}).",
            directory=directory,
            extra={"pid": recorder.pid},
        )
        finished_seen: datetime | None = None
        stop_reason = "window closed"
        while not self._stop:
            now = utcnow()
            if now >= window.record_until:
                break
            if not recorder.running():
                code = recorder.exit_code()
                if finished_seen is not None:
                    stop_reason = f"subscriber exited after the session finished (code {code})"
                    break
                recorder.restarts += 1
                if recorder.restarts > self.s.max_restarts:
                    stop_reason = f"subscriber kept exiting (code {code}); gave up after {self.s.max_restarts} restarts"
                    notify.notify("Recording failed", stop_reason, level="error", directory=directory)
                    break
                notify.notify(
                    "Subscriber restarted",
                    f"It exited with code {code}; restart {recorder.restarts}. The hub drops sockets after about two hours.",
                    level="warning",
                    directory=directory,
                )
                if code not in (0, None):
                    self.tokens.ensure()
                time.sleep(min(5 * recorder.restarts, 60))
                recorder.start()

            status = snapshot_status(directory, recorder.started_at or now) if recorder.started_at else None
            if status in FINISHED_STATUSES and finished_seen is None:
                finished_seen = now
                notify.notify(
                    "Session finished",
                    f"{window.event} {window.label} reported {status}. Stopping in "
                    f"{int(self.s.finalised.total_seconds() // 60)} min.",
                    directory=directory,
                )
            if finished_seen is not None and now - finished_seen >= self.s.finalised:
                stop_reason = f"session {status or 'finished'}"
                break

            write_status(
                directory,
                state="recording",
                session=window.as_json(),
                subscriber={
                    "pid": recorder.pid,
                    "started_at": recorder.started_at.isoformat() if recorder.started_at else None,
                    "restarts": recorder.restarts,
                    "session_status": status,
                },
                token=self.tokens.last_record,
            )
            self._sleep(self.s.poll_seconds)

        recorder.stop()
        laps = max(completed_laps(directory) - laps_before, 0)
        notify.notify(
            "Recording stopped",
            f"{window.event} {window.label}: {stop_reason}. {laps} completed laps recorded this session; "
            f"log {directory / SUBSCRIBER_LOG}.",
            directory=directory,
            extra={"restarts": recorder.restarts, "laps": laps},
        )
        write_status(
            directory,
            state="between_sessions",
            last_session={**window.as_json(), "stop_reason": stop_reason, "laps": laps, "restarts": recorder.restarts},
            token=self.tokens.last_record,
        )
        if not self._stop:
            self._finish(window)

    def _finish(self, window: SessionWindow) -> None:
        self.done.add(window.key)
        self.state["recorded"] = sorted(self.done)
        self.state["last_session"] = window.as_json()
        save_state(self.s.directory, self.state)

    def _sleep(self, seconds: float) -> None:
        end = time.monotonic() + max(seconds, 0)
        while not self._stop and time.monotonic() < end:
            time.sleep(min(1.0, end - time.monotonic()))


# ── CLI ───────────────────────────────────────────────────────────────────────


def print_plan(settings: Settings, count: int) -> int:
    now = utcnow()
    year = settings.year or now.year
    schedule = load_schedule(year, settings.directory)
    windows = session_windows(schedule, lead=settings.lead, grace=settings.grace, now=now)
    done = set(load_state(settings.directory).get("recorded") or [])
    print(f"Now: {_when(now)}")
    record = live_token.read_status()
    if record:
        print(f"Token: {record.get('state')} (expires {record.get('expires_at')}, renewable={record.get('renewable')})")
    else:
        print("Token: no status yet (run live_token.py check)")
    print()
    shown = 0
    for window in windows:
        if shown >= count:
            break
        flag = "recorded" if window.key in done else ("RECORDING NOW" if window.contains(now) else "")
        print(
            f"{window.event} {window.code:<3} {window.label:<18} "
            f"session {_when(window.starts_at)}  record {window.record_from.strftime('%H:%M')}-"
            f"{window.record_until.strftime('%H:%M')} UTC  {flag}"
        )
        shown += 1
    if shown == 0:
        print("No upcoming sessions.")
    return 0


def record_now(settings: Settings, minutes: int) -> int:
    assert_not_cloud_run()
    now = utcnow()
    window = SessionWindow(
        event="Manual",
        round=None,
        code="MAN",
        label="manual recording",
        starts_at=now,
        record_from=now,
        record_until=now + timedelta(minutes=minutes),
    )
    watcher = Watcher(settings)
    watcher.record(window)
    return 0


def build_settings(args: argparse.Namespace) -> Settings:
    return Settings(
        directory=(args.dir or live_dir()).expanduser(),
        lead=timedelta(minutes=args.lead_minutes),
        grace=timedelta(minutes=args.grace_minutes),
        finalised=timedelta(minutes=args.finalised_minutes),
        poll_seconds=args.poll_seconds,
        token_check=timedelta(hours=args.token_check_hours),
        max_restarts=args.max_restarts,
        allow_login=not args.no_login,
        year=args.year,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-start the live import for each session")
    parser.add_argument("--dir", type=Path, default=None, help="Live directory. Default: ~/.local/share/interval/live")
    parser.add_argument("--year", type=int, default=None, help="Season to follow. Default: current year")
    parser.add_argument("--lead-minutes", type=int, default=60, help="Start recording this long before a session")
    parser.add_argument("--grace-minutes", type=int, default=30, help="Keep recording this long past the nominal end")
    parser.add_argument("--finalised-minutes", type=int, default=10, help="Stop this long after the hub says finished")
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--token-check-hours", type=float, default=6, help="How often to run live_token ensure while idle")
    parser.add_argument("--max-restarts", type=int, default=12)
    parser.add_argument("--no-login", action="store_true", help="Never sign in with stored credentials")
    parser.add_argument("--refresh-schedule", action="store_true", help="Reload the schedule from FastF1 first")
    parser.add_argument("--plan", action="store_true", help="Print the upcoming recording windows and exit")
    parser.add_argument("--plan-count", type=int, default=6)
    parser.add_argument("--record-now", type=int, metavar="MINUTES", default=None, help="Record immediately for N minutes, then exit")
    args = parser.parse_args(argv)
    settings = build_settings(args)
    try:
        if args.refresh_schedule:
            load_schedule(settings.year or utcnow().year, settings.directory, refresh=True)
        if args.plan:
            return print_plan(settings, args.plan_count)
        if args.record_now is not None:
            return record_now(settings, args.record_now)
        return Watcher(settings).run()
    except KeyboardInterrupt:
        print("Stopping.")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Watcher failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
