"""Give FastF1 3.9 the same F1 bearer the live archive already uses.

FastF1 attaches ``Authorization: Bearer`` to livetiming downloads on its
own. This module only supplies the token. The raw JWT is never logged.
"""

from __future__ import annotations

import os
from pathlib import Path

_STATUS: str | None = None


def token_path() -> Path:
    override = os.environ.get("F1_SUBSCRIPTION_TOKEN_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "interval" / "f1-subscription-token"


def _read_token() -> str | None:
    try:
        text = token_path().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _password_available() -> bool:
    username = (os.environ.get("F1_USERNAME") or os.environ.get("F1_EMAIL") or "").strip()
    password = (os.environ.get("F1_PASSWORD") or "").strip()
    return bool(username and password)


def configure_fastf1_auth() -> str:
    """Seed FastF1 with the interval token, or allow its password sign-in.

    Returns ``token``, ``password``, or ``missing``.
    """
    import fastf1
    from fastf1.internals.f1account import token_manager
    from fastf1.internals.f1account.tokens import SubscriptionToken

    if _password_available():
        fastf1.set_auth_method("password")

    raw = _read_token()
    if raw:
        try:
            token = SubscriptionToken.from_jwt(raw)
        except Exception:
            token = None
        if token is not None:
            token_manager._token = token
            try:
                token_manager.store(token)
            except OSError:
                pass
            return "token"
    if _password_available():
        return "password"
    return "missing"


def ensure_fastf1_auth() -> str:
    """Configure once per process. Later calls return the same status."""
    global _STATUS
    if _STATUS is None:
        _STATUS = configure_fastf1_auth()
    return _STATUS


def reset_fastf1_auth_status() -> None:
    """Test helper. Does not delete a token FastF1 already stored."""
    global _STATUS
    _STATUS = None
