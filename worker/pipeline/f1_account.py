"""Keep the F1 subscription bearer alive without a browser.

The bearer is a four-day JWT. Formula 1 issues no refresh token, so there
are only three ways to get a new one:

1. Session renewal. The JWT carries the Ascendon ``SessionId`` of the
   account sign-in. Posting that id to ``RetrieveSubscriber`` returns a
   fresh ``subscriptionToken`` while the account session is alive, which
   has been observed to be about thirty days. No password is needed.
2. Password sign-in. The account site runs a PingOne/DaVinci OAuth
   Authorization-Code + PKCE flow. With ``response_mode=pi.flow`` every step
   is a JSON call, so it works from a script. The credentials are read from
   the environment, a mode-600 file, or the macOS keychain. They are sent to
   ``id.formula1.com`` only and are never written anywhere by this module.
3. Browser capture. ``live_token.py`` reads the ``login-session`` cookie from
   a signed-in Chrome. This is the bootstrap when 1 and 2 are not available.

Nothing in this module prints or logs a token or a password.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jwt
import requests

ACCOUNT_ORIGIN = "https://account.formula1.com"
IDP_ORIGIN = "https://id.formula1.com"
AUTHORIZE_URL = f"{IDP_ORIGIN}/as/authorize"
TOKEN_URL = f"{IDP_ORIGIN}/as/token"
CONFIG_SCRIPT_URL = f"{ACCOUNT_ORIGIN}/scripts/main.min.js"

RETRIEVE_SUBSCRIBER_URL = "https://api.formula1.com/v1/account/Subscriber/RetrieveSubscriber"
# Public web-client identifiers that the formula1.com frontend sends itself.
F1_API_KEY = "fCUCjWrKPu9ylJwRAv8BpGLEgiAuThx7"
F1_SYSTEM_ID = "60a9ad84-e93d-480f-80d6-af37494f2e22"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en;q=0.9"}
PING_SDK_HEADERS = {"X-Requested-With": "ping-sdk"}
TIMEOUT = (5, 30)

ENV_USERNAME = "F1_USERNAME"
# The earlier agent VMs stored the account as F1_EMAIL; both names work.
ENV_USERNAME_ALIAS = "F1_EMAIL"
ENV_PASSWORD = "F1_PASSWORD"
ENV_CREDENTIALS_FILE = "F1_CREDENTIALS_FILE"
ENV_KEYCHAIN_SERVICE = "F1_KEYCHAIN_SERVICE"
DEFAULT_KEYCHAIN_SERVICE = "interval-f1-account"

_DAVINCI_OBJECT = re.compile(r"\bdavinci:\{([^}]*)\}")


class F1AccountError(RuntimeError):
    """Base error for account operations."""


class SignInRequired(F1AccountError):
    """The stored session is gone and no credentials can replace it.

    A human has to sign in again (browser capture) or provide credentials.
    """


class TemporaryFailure(F1AccountError):
    """Network or upstream trouble. Retrying later is reasonable."""


# ── token inspection ──────────────────────────────────────────────────────────


def claims(token: str) -> dict[str, Any]:
    """Unverified claims. ``live_token.verify_token`` does the signature check."""
    return jwt.decode(token, options={"verify_signature": False})


def expires_at(token: str) -> datetime | None:
    exp = claims(token).get("exp")
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, timezone.utc)
    return None


def session_id(token: str) -> str | None:
    value = claims(token).get("SessionId")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def session_expires_at(token: str) -> datetime | None:
    """Expiry of the account session embedded in ``SessionId``, if it is a JWT."""
    sid = session_id(token)
    if not sid or sid.count(".") != 2:
        return None
    try:
        exp = jwt.decode(sid, options={"verify_signature": False}).get("exp")
    except jwt.PyJWTError:
        return None
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, timezone.utc)
    return None


def session_is_renewable(token: str, now: datetime | None = None) -> bool:
    """True when the token names a session that has not visibly expired."""
    sid = session_id(token)
    if not sid:
        return False
    session_exp = session_expires_at(token)
    if session_exp is None:
        return True
    return session_exp > (now or datetime.now(timezone.utc))


# ── 1. session renewal ────────────────────────────────────────────────────────


def renew_with_session(token: str, *, session: requests.Session | None = None) -> str:
    """Trade the session behind ``token`` for a fresh subscription token.

    Raises ``SignInRequired`` when the session is gone (401/403 or no id),
    ``TemporaryFailure`` for anything that may pass on retry.
    """
    sid = session_id(token)
    if not sid:
        raise SignInRequired("The stored token has no SessionId; capture a new one from the browser.")
    if not session_is_renewable(token):
        raise SignInRequired("The account session behind the token has expired; sign in again.")

    headers = {
        **DEFAULT_HEADERS,
        "Content-Type": "application/json",
        "apikey": F1_API_KEY,
        "CD-SystemId": F1_SYSTEM_ID,
        "cd-sessionid": sid,
        "orderSubmitted": "true",
    }
    http = session or requests.Session()
    try:
        response = http.post(
            RETRIEVE_SUBSCRIBER_URL,
            headers=headers,
            json={},
            timeout=TIMEOUT,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise TemporaryFailure(f"RetrieveSubscriber request failed: {exc}") from exc

    if response.status_code in (401, 403):
        raise SignInRequired(f"RetrieveSubscriber rejected the session (HTTP {response.status_code}).")
    if response.status_code != 200:
        raise TemporaryFailure(f"RetrieveSubscriber returned HTTP {response.status_code}.")
    try:
        body = response.json()
    except ValueError as exc:
        raise TemporaryFailure("RetrieveSubscriber did not return JSON.") from exc

    data = body.get("data") if isinstance(body, dict) else None
    fresh = data.get("subscriptionToken") if isinstance(data, dict) else None
    if not isinstance(fresh, str) or not fresh.strip():
        raise TemporaryFailure("RetrieveSubscriber returned no subscriptionToken.")
    fresh = fresh.strip()

    old_exp, new_exp = expires_at(token), expires_at(fresh)
    if new_exp is None:
        raise TemporaryFailure("Renewed token has no expiry.")
    if old_exp is not None and new_exp <= old_exp:
        raise TemporaryFailure("Renewed token does not outlive the current one.")
    return fresh


# ── 2. password sign-in (PingOne / DaVinci, redirectless) ─────────────────────


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str
    source: str


def credentials_from_environment() -> Credentials | None:
    """Find account credentials without prompting.

    Order: ``F1_USERNAME``/``F1_PASSWORD``; the JSON file named by
    ``F1_CREDENTIALS_FILE`` (``{"username": ..., "password": ...}``, mode
    600); the macOS keychain item whose service is ``F1_KEYCHAIN_SERVICE``
    (default ``interval-f1-account``). Returns ``None`` when nothing is set.
    """
    username = os.environ.get(ENV_USERNAME) or os.environ.get(ENV_USERNAME_ALIAS)
    password = os.environ.get(ENV_PASSWORD)
    if username and password:
        return Credentials(username, password, "env")

    file_name = os.environ.get(ENV_CREDENTIALS_FILE)
    if file_name:
        path = Path(file_name).expanduser()
        if path.is_file():
            try:
                data = json.loads(path.read_text())
            except ValueError as exc:
                raise F1AccountError(f"{path} is not valid JSON.") from exc
            username = data.get("username") or data.get("email")
            password = data.get("password")
            if username and password:
                return Credentials(str(username), str(password), "file")

    found = _credentials_from_keychain(os.environ.get(ENV_KEYCHAIN_SERVICE, DEFAULT_KEYCHAIN_SERVICE))
    if found:
        return found
    return None


def _credentials_from_keychain(service: str) -> Credentials | None:
    if platform.system() != "Darwin":
        return None
    try:
        meta = subprocess.run(
            ["security", "find-generic-password", "-s", service],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if meta.returncode != 0:
            return None
        account = re.search(r'"acct"<blob>="([^"]*)"', meta.stdout + meta.stderr)
        secret = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if not account or secret.returncode != 0 or not secret.stdout.strip():
        return None
    return Credentials(account.group(1), secret.stdout.strip(), "keychain")


@dataclass(frozen=True)
class OAuthConfig:
    client_id: str
    policy_id: str


def parse_frontend_config(script: str) -> OAuthConfig:
    """Pull ``clientId`` and ``acrValues`` from the account site's bundle.

    The endpoint urls are fixed, but F1 can rotate these two values, so they
    are read from the public frontend script at sign-in time.
    """
    match = _DAVINCI_OBJECT.search(script)
    if not match:
        raise F1AccountError(f"No davinci config object found in {CONFIG_SCRIPT_URL}.")

    def field(name: str) -> str:
        found = re.search(rf'\b{name}:"([^"]+)"', match.group(1))
        if not found:
            raise F1AccountError(f"Account config is missing {name}.")
        return found.group(1)

    return OAuthConfig(client_id=field("clientId"), policy_id=field("acrValues"))


def _fetch_config(http: requests.Session) -> OAuthConfig:
    response = http.get(CONFIG_SCRIPT_URL, timeout=TIMEOUT)
    response.raise_for_status()
    return parse_frontend_config(response.text)


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def login_with_password(username: str, password: str, *, session: requests.Session | None = None) -> str:
    """Sign in and return the subscription token.

    Raises ``SignInRequired`` for rejected credentials, ``TemporaryFailure``
    for network trouble, ``F1AccountError`` when the flow shape changed.
    """
    http = session or requests.Session()
    http.headers.update(DEFAULT_HEADERS)
    try:
        config = _fetch_config(http)
        access_token = _run_login_flow(http, config, username, password)
    except requests.RequestException as exc:
        raise TemporaryFailure(f"Sign-in request failed: {exc}") from exc

    try:
        token_claims = jwt.decode(access_token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise F1AccountError("The access token could not be decoded.") from exc
    subscription = token_claims.get("subscriptionToken")
    if not isinstance(subscription, str) or not subscription:
        raise SignInRequired("The account signed in but carries no F1 TV subscription token.")
    return subscription


def _run_login_flow(http: requests.Session, config: OAuthConfig, username: str, password: str) -> str:
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(24)

    start = http.get(
        AUTHORIZE_URL,
        params={
            "client_id": config.client_id,
            "response_type": "code",
            "response_mode": "pi.flow",
            "scope": "openid",
            "state": state,
            "nonce": secrets.token_urlsafe(24),
            "code_challenge": _code_challenge(verifier),
            "code_challenge_method": "S256",
            "acr_values": config.policy_id,
        },
        headers=PING_SDK_HEADERS,
        timeout=TIMEOUT,
    )
    start.raise_for_status()
    form = start.json()
    try:
        submit_url = form["_links"]["next"]["href"]
        interaction_id = form["interactionId"]
        flow_id = form["id"]
        event_name = form["eventName"]
    except (KeyError, TypeError) as exc:
        raise F1AccountError("Unexpected response when starting the sign-in.") from exc
    if not submit_url.startswith(f"{IDP_ORIGIN}/"):
        raise F1AccountError(f"Refusing to send credentials to {submit_url}.")

    submitted = http.post(
        submit_url,
        json={
            "id": flow_id,
            "eventName": event_name,
            "interactionId": interaction_id,
            "parameters": {
                "eventType": "submit",
                "data": {
                    "actionKey": "SIGNIN",
                    "formData": {"username": username, "password": password},
                },
            },
        },
        headers={**PING_SDK_HEADERS, "interactionId": interaction_id},
        timeout=TIMEOUT,
    )
    code = _authorization_code(submitted, state)

    exchanged = http.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "code": code,
            "code_verifier": verifier,
        },
        timeout=TIMEOUT,
    )
    exchanged.raise_for_status()
    try:
        return exchanged.json()["access_token"]
    except (ValueError, KeyError, TypeError) as exc:
        raise F1AccountError("No access token in the token response.") from exc


def _authorization_code(response: requests.Response, state: str) -> str:
    try:
        data = response.json()
    except ValueError:
        if response.status_code in (401, 403, 429):
            raise SignInRequired(f"The sign-in was blocked (HTTP {response.status_code}).") from None
        response.raise_for_status()
        raise F1AccountError("Unexpected response from the sign-in.") from None

    if data.get("status") != "COMPLETED":
        message = data.get("message") or f"Sign-in failed (HTTP {response.status_code})."
        raise SignInRequired(str(message))
    authorize = data.get("authorizeResponse") or {}
    if authorize.get("state") != state:
        raise F1AccountError("Sign-in failed: state mismatch.")
    code = authorize.get("code")
    if not isinstance(code, str) or not code:
        raise F1AccountError("Sign-in failed: no authorization code.")
    return code
