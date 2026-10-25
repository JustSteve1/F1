"""Hold a valid F1 subscription bearer on this machine.

The token is a four-day JWT. This module owns its lifecycle:

- ``capture``  reads it from the signed-in debug Chrome (bootstrap)
- ``renew``    trades the account session inside the token for a new one
- ``login``    signs in with stored credentials when the session is gone
- ``ensure``   does whichever of the above is needed, in that order
- ``check``    verifies the stored token and prints its status

The token is written outside the git repo, mode 600, and is not printed.
A redacted status file next to it (``*.status.json``) feeds the watcher
and the ``/live`` page.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
import requests
import websocket
from jwt.algorithms import RSAAlgorithm

sys.path.insert(0, str(Path(__file__).resolve().parent))

import f1_account  # noqa: E402

JWKS_URL = "https://api.formula1.com/static/jwks.json"
DEVTOOLS_URL = os.environ.get("CHROME_DEVTOOLS_URL", "http://127.0.0.1:9222")
COOKIE_URLS = [
    "https://www.formula1.com/",
    "https://account.formula1.com/",
    "https://formula1.com/",
]
# FastF1's auth handoff calls the decoded value loginSession. Chrome stores
# the same cookie as login-session.
LOGIN_COOKIE_NAMES = ("login-session", "loginSession")

# Renew once this little life is left. F1 Sensor renews in the final 24 h;
# a day leaves room for retries before a session starts.
RENEW_WINDOW = timedelta(hours=24)
# Below this the token is treated as unusable for a session that is starting.
MIN_LIFE = timedelta(minutes=5)

SIGN_IN_HELP = (
    "Sign in at https://account.formula1.com/#/en/login in the debug Chrome, "
    "open https://www.formula1.com/en/timing/f1-live, then run "
    "`python3 worker/pipeline/live_token.py capture`. Or set F1_USERNAME and "
    "F1_PASSWORD (or F1_CREDENTIALS_FILE / the macOS keychain) so `ensure` can sign in itself."
)


class SignInRequired(f1_account.SignInRequired):
    """Re-exported so callers can catch one type."""


def token_path() -> Path:
    override = os.environ.get("F1_SUBSCRIPTION_TOKEN_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "interval" / "f1-subscription-token"


def status_path(path: Path | None = None) -> Path:
    base = path or token_path()
    return base.with_name(base.name + ".status.json")


# ── browser capture ───────────────────────────────────────────────────────────


def _cdp(
    ws: websocket.WebSocket,
    msg_id: int,
    method: str,
    params: dict | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"id": msg_id, "method": method}
    if params:
        message["params"] = params
    if session_id:
        message["sessionId"] = session_id
    ws.send(json.dumps(message))
    while True:
        data = json.loads(ws.recv())
        if data.get("id") != msg_id:
            continue
        if "error" in data:
            raise RuntimeError(f"DevTools {method} failed: {data['error']}")
        return data.get("result") or {}


def read_login_session(devtools_url: str = DEVTOOLS_URL) -> str:
    try:
        with urllib.request.urlopen(devtools_url.rstrip("/") + "/json/version", timeout=5) as response:
            version = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            "Chrome DevTools is not available. Sign in at "
            "https://www.formula1.com/en/timing/f1-live in the debug Chrome "
            f"and leave it running ({devtools_url})."
        ) from exc

    ws_url = version.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError("Chrome DevTools did not return a websocket URL.")

    ws = websocket.create_connection(ws_url, timeout=15)
    try:
        targets = _cdp(ws, 1, "Target.getTargets").get("targetInfos") or []
        page = next(
            (
                target
                for target in targets
                if target.get("type") == "page" and "formula1.com" in (target.get("url") or "")
            ),
            None,
        )
        if page is None:
            raise RuntimeError(
                "No formula1.com tab is open in the debug Chrome. "
                "Open the live timing page while signed in, then retry."
            )
        attached = _cdp(
            ws,
            2,
            "Target.attachToTarget",
            {"targetId": page["targetId"], "flatten": True},
        )
        session_id = attached["sessionId"]
        _cdp(ws, 3, "Network.enable", {}, session_id)
        cookies = _cdp(
            ws,
            4,
            "Network.getCookies",
            {"urls": COOKIE_URLS},
            session_id,
        ).get("cookies") or []
    finally:
        ws.close()

    for name in LOGIN_COOKIE_NAMES:
        for cookie in cookies:
            if cookie.get("name") == name and cookie.get("value"):
                return cookie["value"]

    names = ", ".join(
        sorted({cookie.get("name", "") for cookie in cookies if cookie.get("name")})
    )
    raise RuntimeError(
        "Signed-in Chrome has no loginSession cookie. "
        f"Cookie names seen: {names or '(none)'}."
    )


def token_from_login_session(raw: str) -> str:
    text = urllib.parse.unquote(raw or "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("loginSession cookie is not JSON.") from exc
    token = None
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, dict):
            token = inner.get("subscriptionToken")
    if not isinstance(token, str) or not token:
        raise RuntimeError("loginSession has no data.subscriptionToken.")
    return token


# ── verification and storage ──────────────────────────────────────────────────


def _public_key(token: str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise RuntimeError("Subscription token header has no kid.")
    response = requests.get(JWKS_URL, timeout=20)
    response.raise_for_status()
    for key in (response.json().get("keys") or []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key)
    raise RuntimeError(f"No JWKS key matches kid {kid}.")


def verify_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _public_key(token),
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def write_token(token: str, path: Path | None = None) -> Path:
    destination = path or token_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(token)
    os.chmod(destination, 0o600)
    return destination


def _expiry(claims: dict[str, Any]) -> datetime | None:
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, timezone.utc)
    return None


def time_left(claims: dict[str, Any], now: datetime | None = None) -> timedelta | None:
    expiry = _expiry(claims)
    if expiry is None:
        return None
    return expiry - (now or datetime.now(timezone.utc))


def needs_renewal(claims: dict[str, Any], now: datetime | None = None) -> bool:
    left = time_left(claims, now)
    return left is None or left <= RENEW_WINDOW


def is_usable(claims: dict[str, Any], now: datetime | None = None) -> bool:
    left = time_left(claims, now)
    return left is not None and left > MIN_LIFE


def format_status(claims: dict[str, Any], path: Path) -> str:
    expiry = _expiry(claims)
    return (
        f"Token file: {path}\n"
        f"Expires: {expiry.isoformat() if expiry else 'unknown'}\n"
        f"Subscription status: {claims.get('SubscriptionStatus')}\n"
        f"Subscribed product: {claims.get('SubscribedProduct')}"
    )


def status_record(
    claims: dict[str, Any] | None,
    *,
    token: str | None = None,
    source: str | None = None,
    action: str,
    error: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Redacted view of the token for the watcher and the UI. No token bytes."""
    now = now or datetime.now(timezone.utc)
    record: dict[str, Any] = {
        "checked_at": now.isoformat(),
        "action": action,
        "source": source,
        "error": error,
        "present": claims is not None,
        "expires_at": None,
        "seconds_left": None,
        "state": "missing",
        "subscription_status": None,
        "subscribed_product": None,
        "session_expires_at": None,
        "renewable": False,
    }
    if claims is None:
        return record
    expiry = _expiry(claims)
    left = time_left(claims, now)
    record.update(
        {
            "expires_at": expiry.isoformat() if expiry else None,
            "seconds_left": int(left.total_seconds()) if left is not None else None,
            "subscription_status": claims.get("SubscriptionStatus"),
            "subscribed_product": claims.get("SubscribedProduct"),
        }
    )
    if left is None or left <= timedelta(0):
        record["state"] = "expired"
    elif left <= RENEW_WINDOW:
        record["state"] = "expiring"
    else:
        record["state"] = "valid"
    if token:
        session_exp = f1_account.session_expires_at(token)
        record["session_expires_at"] = session_exp.isoformat() if session_exp else None
        record["renewable"] = f1_account.session_is_renewable(token, now)
    return record


def write_status(record: dict[str, Any], path: Path | None = None) -> Path:
    destination = status_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2))
    os.chmod(temporary, 0o600)
    temporary.replace(destination)
    return destination


def read_status(path: Path | None = None) -> dict[str, Any] | None:
    destination = status_path(path)
    try:
        return json.loads(destination.read_text())
    except (OSError, ValueError):
        return None


# ── operations ────────────────────────────────────────────────────────────────


def capture(devtools_url: str = DEVTOOLS_URL) -> tuple[Path, dict[str, Any]]:
    token = token_from_login_session(read_login_session(devtools_url))
    claims = verify_token(token)
    path = write_token(token)
    write_status(status_record(claims, token=token, source="browser", action="captured"), path)
    return path, claims


def check_stored(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    destination = path or token_path()
    if not destination.is_file():
        raise RuntimeError(f"No token file at {destination}. Capture one first.")
    token = destination.read_text().strip()
    if not token:
        raise RuntimeError(f"Token file {destination} is empty.")
    return destination, verify_token(token)


def _stored_token(path: Path) -> str | None:
    try:
        token = path.read_text().strip()
    except OSError:
        return None
    return token or None


def renew(path: Path | None = None, *, force: bool = False) -> tuple[Path, dict[str, Any], str]:
    """Renew through the account session. Returns (path, claims, action)."""
    destination = path or token_path()
    token = _stored_token(destination)
    if token is None:
        raise SignInRequired(f"No token file at {destination}. {SIGN_IN_HELP}")
    current = f1_account.claims(token)
    if not force and not needs_renewal(current):
        return destination, current, "kept"
    try:
        fresh = f1_account.renew_with_session(token)
    except f1_account.SignInRequired as exc:
        write_status(status_record(current, token=token, source="renewal", action="renew_failed", error=str(exc)), destination)
        raise SignInRequired(f"{exc} {SIGN_IN_HELP}") from exc
    except f1_account.TemporaryFailure as exc:
        write_status(status_record(current, token=token, source="renewal", action="renew_failed", error=str(exc)), destination)
        raise
    claims = verify_token(fresh)
    write_token(fresh, destination)
    write_status(status_record(claims, token=fresh, source="renewal", action="renewed"), destination)
    return destination, claims, "renewed"


def login(path: Path | None = None) -> tuple[Path, dict[str, Any], str]:
    """Sign in with stored credentials. Returns (path, claims, action)."""
    destination = path or token_path()
    credentials = f1_account.credentials_from_environment()
    if credentials is None:
        raise SignInRequired(f"No F1 account credentials are configured. {SIGN_IN_HELP}")
    try:
        fresh = f1_account.login_with_password(credentials.username, credentials.password)
    except f1_account.SignInRequired as exc:
        write_status(status_record(None, source=f"password:{credentials.source}", action="login_failed", error=str(exc)), destination)
        raise SignInRequired(f"{exc} {SIGN_IN_HELP}") from exc
    claims = verify_token(fresh)
    write_token(fresh, destination)
    write_status(
        status_record(claims, token=fresh, source=f"password:{credentials.source}", action="signed_in"),
        destination,
    )
    return destination, claims, "signed_in"


def ensure(path: Path | None = None, *, allow_login: bool = True) -> tuple[Path, dict[str, Any], str]:
    """Return a token with more than ``RENEW_WINDOW`` of life, or raise.

    Order: keep the stored token if it is fresh; renew through the account
    session; sign in with stored credentials. Raises ``SignInRequired`` when
    a human has to act, ``f1_account.TemporaryFailure`` when a retry may do.
    """
    destination = path or token_path()
    token = _stored_token(destination)
    current = None
    if token is not None:
        try:
            current = f1_account.claims(token)
        except jwt.PyJWTError:
            current = None
    if current is not None and not needs_renewal(current):
        write_status(status_record(current, token=token, action="kept"), destination)
        return destination, current, "kept"

    renewal_error: Exception | None = None
    if token is not None and current is not None:
        try:
            return renew(destination, force=True)
        except (f1_account.SignInRequired, f1_account.TemporaryFailure) as exc:
            renewal_error = exc

    if allow_login and f1_account.credentials_from_environment() is not None:
        try:
            return login(destination)
        except f1_account.TemporaryFailure as exc:
            if renewal_error is None:
                raise
            raise f1_account.TemporaryFailure(f"{renewal_error}; then {exc}") from exc

    if current is not None and is_usable(current):
        # Nothing could extend it, but it still opens the hub for now. The
        # status file carries the reason so the watcher can say so.
        write_status(
            status_record(
                current,
                token=token,
                action="kept_expiring",
                error=str(renewal_error) if renewal_error else None,
            ),
            destination,
        )
        return destination, current, "kept_expiring"

    if isinstance(renewal_error, f1_account.TemporaryFailure):
        raise renewal_error
    write_status(status_record(current, token=token, action="sign_in_required", error=str(renewal_error) if renewal_error else None), destination)
    reason = f"{renewal_error} " if renewal_error else ""
    raise SignInRequired(f"{reason}{SIGN_IN_HELP}")


# ── CLI ───────────────────────────────────────────────────────────────────────


def _print_result(path: Path, claims: dict[str, Any], action: str | None = None) -> None:
    if action:
        print(f"Action: {action}")
    print(format_status(claims, path))
    left = time_left(claims)
    if left is not None:
        hours = left.total_seconds() / 3600
        print(f"Time left: {hours:.1f} h")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture, check, renew, or sign in for the F1 subscription bearer")
    parser.add_argument(
        "command",
        nargs="?",
        default="capture",
        choices=["capture", "check", "renew", "login", "ensure", "status"],
        help="capture (default) reads Chrome; check verifies the file; renew uses the account session; "
        "login uses stored credentials; ensure picks whichever is needed; status prints the redacted JSON",
    )
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--force", action="store_true", help="renew even if the token is still fresh")
    parser.add_argument("--no-login", action="store_true", help="ensure: never use stored credentials")
    parser.add_argument("--devtools-url", default=DEVTOOLS_URL)
    args = parser.parse_args(argv)
    command = "check" if args.check else args.command

    try:
        if command == "capture":
            path, claims = capture(args.devtools_url)
            _print_result(path, claims, "captured")
        elif command == "check":
            path, claims = check_stored()
            write_status(status_record(claims, token=_stored_token(path), action="checked"), path)
            _print_result(path, claims)
        elif command == "renew":
            _print_result(*renew(force=args.force))
        elif command == "login":
            _print_result(*login())
        elif command == "ensure":
            _print_result(*ensure(allow_login=not args.no_login))
        elif command == "status":
            record = read_status()
            if record is None:
                path = token_path()
                token = _stored_token(path)
                record = status_record(f1_account.claims(token) if token else None, token=token, action="status")
            print(json.dumps(record, indent=2))
    except f1_account.TemporaryFailure as exc:
        print(f"Temporary failure: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Bearer {command} failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
