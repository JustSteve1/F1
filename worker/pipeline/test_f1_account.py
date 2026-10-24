"""Session renewal and sign-in plumbing, without touching formula1.com."""

from __future__ import annotations

import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import f1_account  # noqa: E402


def _jwt(**claims) -> str:
    return jwt.encode(claims, key=None, algorithm="none")


def _token(hours_left: float, session_hours_left: float | None = 24 * 20) -> str:
    exp = int(time.time() + hours_left * 3600)
    session = None
    if session_hours_left is not None:
        session = _jwt(exp=int(time.time() + session_hours_left * 3600), sid="abc")
    claims = {"exp": exp, "SubscriptionStatus": "active", "SubscribedProduct": "F1 TV Access Monthly"}
    if session is not None:
        claims["SessionId"] = session
    return _jwt(**claims)


class _Response:
    def __init__(self, status_code: int, body=None):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class _Http:
    def __init__(self, response: _Response):
        self.response = response
        self.calls: list[dict] = []

    def post(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class ClaimsTests(unittest.TestCase):
    def test_session_id_and_embedded_expiry_are_read(self) -> None:
        token = _token(hours_left=50, session_hours_left=24 * 10)
        self.assertTrue(f1_account.session_id(token))
        session_exp = f1_account.session_expires_at(token)
        self.assertIsNotNone(session_exp)
        self.assertGreater(session_exp, datetime.now(timezone.utc) + timedelta(days=9))
        self.assertTrue(f1_account.session_is_renewable(token))

    def test_token_without_session_is_not_renewable(self) -> None:
        self.assertFalse(f1_account.session_is_renewable(_token(50, session_hours_left=None)))

    def test_expired_session_is_not_renewable(self) -> None:
        self.assertFalse(f1_account.session_is_renewable(_token(50, session_hours_left=-1)))


class RenewalTests(unittest.TestCase):
    def test_renewal_returns_the_longer_lived_token(self) -> None:
        current = _token(hours_left=10)
        fresh = _token(hours_left=96)
        http = _Http(_Response(200, {"data": {"subscriptionToken": fresh}}))
        result = f1_account.renew_with_session(current, session=http)
        self.assertEqual(result, fresh)
        headers = http.calls[0]["headers"]
        self.assertEqual(headers["cd-sessionid"], f1_account.session_id(current))
        self.assertEqual(headers["apikey"], f1_account.F1_API_KEY)

    def test_rejected_session_requires_sign_in(self) -> None:
        with self.assertRaises(f1_account.SignInRequired):
            f1_account.renew_with_session(_token(10), session=_Http(_Response(401)))

    def test_server_trouble_is_temporary(self) -> None:
        with self.assertRaises(f1_account.TemporaryFailure):
            f1_account.renew_with_session(_token(10), session=_Http(_Response(503)))

    def test_a_token_that_does_not_outlive_the_current_one_is_rejected(self) -> None:
        current = _token(hours_left=10)
        stale = _token(hours_left=5)
        with self.assertRaises(f1_account.TemporaryFailure):
            f1_account.renew_with_session(current, session=_Http(_Response(200, {"data": {"subscriptionToken": stale}})))

    def test_missing_session_id_requires_sign_in_without_a_request(self) -> None:
        http = _Http(_Response(200))
        with self.assertRaises(f1_account.SignInRequired):
            f1_account.renew_with_session(_token(10, session_hours_left=None), session=http)
        self.assertEqual(http.calls, [])


class ConfigTests(unittest.TestCase):
    def test_client_id_and_policy_are_scraped(self) -> None:
        script = 'var x={davinci:{clientId:"client-123",acrValues:"policy-456",env:"prod"},other:1};'
        config = f1_account.parse_frontend_config(script)
        self.assertEqual(config.client_id, "client-123")
        self.assertEqual(config.policy_id, "policy-456")

    def test_missing_config_raises(self) -> None:
        with self.assertRaises(f1_account.F1AccountError):
            f1_account.parse_frontend_config("var x = 1;")


class CredentialTests(unittest.TestCase):
    def test_environment_wins(self) -> None:
        env = {f1_account.ENV_USERNAME: "a@b.c", f1_account.ENV_PASSWORD: "pw"}
        with mock.patch.dict(os.environ, env, clear=False):
            found = f1_account.credentials_from_environment()
        self.assertEqual((found.username, found.password, found.source), ("a@b.c", "pw", "env"))

    def test_legacy_email_name_is_accepted(self) -> None:
        env = {f1_account.ENV_USERNAME: "", f1_account.ENV_USERNAME_ALIAS: "a@b.c", f1_account.ENV_PASSWORD: "pw"}
        with mock.patch.dict(os.environ, env, clear=False):
            found = f1_account.credentials_from_environment()
        self.assertEqual(found.username, "a@b.c")

    def test_nothing_configured_is_none(self) -> None:
        cleared = {
            f1_account.ENV_USERNAME: "",
            f1_account.ENV_USERNAME_ALIAS: "",
            f1_account.ENV_PASSWORD: "",
            f1_account.ENV_CREDENTIALS_FILE: "",
        }
        with mock.patch.dict(os.environ, cleared, clear=False), mock.patch.object(
            f1_account, "_credentials_from_keychain", return_value=None
        ):
            self.assertIsNone(f1_account.credentials_from_environment())


if __name__ == "__main__":
    unittest.main()
