"""Read the F1 subscription bearer from the signed-in Chrome window.

The password file is never opened. The token is written outside the git
repo, mode 600, and is not printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jwt
import requests
import websocket
from jwt.algorithms import RSAAlgorithm

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


def token_path() -> Path:
    override = os.environ.get("F1_SUBSCRIPTION_TOKEN_FILE")
    if override:
        return Path(override)
    return Path.home() / ".config" / "interval" / "f1-subscription-token"


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


def format_status(claims: dict[str, Any], path: Path) -> str:
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        expiry = datetime.fromtimestamp(exp, timezone.utc).isoformat()
    else:
        expiry = "unknown"
    return (
        f"Token file: {path}\n"
        f"Expires: {expiry}\n"
        f"Subscription status: {claims.get('SubscriptionStatus')}\n"
        f"Subscribed product: {claims.get('SubscribedProduct')}"
    )


def capture(devtools_url: str = DEVTOOLS_URL) -> tuple[Path, dict[str, Any]]:
    token = token_from_login_session(read_login_session(devtools_url))
    claims = verify_token(token)
    path = write_token(token)
    return path, claims


def check_stored(path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    destination = path or token_path()
    if not destination.is_file():
        raise RuntimeError(f"No token file at {destination}. Capture one first.")
    token = destination.read_text().strip()
    if not token:
        raise RuntimeError(f"Token file {destination} is empty.")
    return destination, verify_token(token)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture or check the F1 subscription bearer")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the token already on disk instead of reading Chrome",
    )
    parser.add_argument("--devtools-url", default=DEVTOOLS_URL)
    args = parser.parse_args(argv)
    try:
        if args.check:
            path, claims = check_stored()
        else:
            path, claims = capture(args.devtools_url)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Bearer capture failed: {exc}", file=sys.stderr)
        return 1
    print(format_status(claims, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
