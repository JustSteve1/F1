"""Token lifecycle: keep, renew, sign in, or ask a human."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import f1_account  # noqa: E402
import live_token  # noqa: E402


def _jwt(**claims) -> str:
    return jwt.encode(claims, key=None, algorithm="none")


def _token(hours_left: float, with_session: bool = True) -> str:
    claims = {
        "exp": int(time.time() + hours_left * 3600),
        "SubscriptionStatus": "active",
        "SubscribedProduct": "F1 TV Access Monthly",
    }
    if with_session:
        claims["SessionId"] = _jwt(exp=int(time.time() + 20 * 86400))
    return _jwt(**claims)


def _unverified(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


class PolicyTests(unittest.TestCase):
    def test_renewal_window_and_usability(self) -> None:
        fresh = _unverified(_token(72))
        soon = _unverified(_token(5))
        dead = _unverified(_token(-1))
        self.assertFalse(live_token.needs_renewal(fresh))
        self.assertTrue(live_token.needs_renewal(soon))
        self.assertTrue(live_token.is_usable(soon))
        self.assertFalse(live_token.is_usable(dead))

    def test_status_record_is_redacted(self) -> None:
        token = _token(72)
        record = live_token.status_record(_unverified(token), token=token, action="checked")
        self.assertEqual(record["state"], "valid")
        self.assertTrue(record["renewable"])
        self.assertEqual(record["subscribed_product"], "F1 TV Access Monthly")
        self.assertNotIn(token, json.dumps(record))
        self.assertEqual(live_token.status_record(None, action="status")["state"], "missing")
        self.assertEqual(live_token.status_record(_unverified(_token(5)), action="x")["state"], "expiring")
        self.assertEqual(live_token.status_record(_unverified(_token(-5)), action="x")["state"], "expired")


class EnsureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "token"
        patches = [
            mock.patch.object(live_token, "verify_token", side_effect=_unverified),
            mock.patch.dict(
                os.environ,
                {f1_account.ENV_USERNAME: "", f1_account.ENV_PASSWORD: "", f1_account.ENV_CREDENTIALS_FILE: ""},
            ),
            mock.patch.object(f1_account, "_credentials_from_keychain", return_value=None),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _store(self, token: str) -> None:
        live_token.write_token(token, self.path)

    def _status(self) -> dict:
        return json.loads(live_token.status_path(self.path).read_text())

    def test_fresh_token_is_kept(self) -> None:
        self._store(_token(72))
        with mock.patch.object(f1_account, "renew_with_session") as renew:
            _, _, action = live_token.ensure(self.path)
        self.assertEqual(action, "kept")
        renew.assert_not_called()
        self.assertEqual(self._status()["action"], "kept")

    def test_expiring_token_is_renewed_and_written(self) -> None:
        self._store(_token(5))
        fresh = _token(96)
        with mock.patch.object(f1_account, "renew_with_session", return_value=fresh):
            _, claims, action = live_token.ensure(self.path)
        self.assertEqual(action, "renewed")
        self.assertEqual(self.path.read_text(), fresh)
        self.assertEqual(claims["exp"], _unverified(fresh)["exp"])
        self.assertEqual(self._status()["source"], "renewal")
        self.assertEqual(oct(self.path.stat().st_mode & 0o777), oct(0o600))

    def test_rejected_session_with_credentials_signs_in(self) -> None:
        self._store(_token(5))
        fresh = _token(96)
        creds = f1_account.Credentials("a@b.c", "pw", "env")
        with mock.patch.object(
            f1_account, "renew_with_session", side_effect=f1_account.SignInRequired("gone")
        ), mock.patch.object(f1_account, "credentials_from_environment", return_value=creds), mock.patch.object(
            f1_account, "login_with_password", return_value=fresh
        ) as login:
            _, _, action = live_token.ensure(self.path)
        self.assertEqual(action, "signed_in")
        login.assert_called_once_with("a@b.c", "pw")
        self.assertEqual(self._status()["source"], "password:env")

    def test_rejected_session_without_credentials_keeps_a_usable_token(self) -> None:
        self._store(_token(5))
        with mock.patch.object(f1_account, "renew_with_session", side_effect=f1_account.SignInRequired("gone")):
            _, _, action = live_token.ensure(self.path)
        self.assertEqual(action, "kept_expiring")
        self.assertIn("gone", self._status()["error"])

    def test_dead_token_without_any_path_asks_a_human(self) -> None:
        self._store(_token(-1))
        with mock.patch.object(f1_account, "renew_with_session", side_effect=f1_account.SignInRequired("gone")):
            with self.assertRaises(live_token.SignInRequired):
                live_token.ensure(self.path)
        self.assertEqual(self._status()["action"], "sign_in_required")

    def test_temporary_failure_on_a_dead_token_is_passed_through(self) -> None:
        self._store(_token(-1))
        with mock.patch.object(f1_account, "renew_with_session", side_effect=f1_account.TemporaryFailure("503")):
            with self.assertRaises(f1_account.TemporaryFailure):
                live_token.ensure(self.path)

    def test_missing_file_asks_a_human(self) -> None:
        with self.assertRaises(live_token.SignInRequired):
            live_token.ensure(self.path)

    def test_renew_without_force_keeps_a_fresh_token(self) -> None:
        self._store(_token(72))
        with mock.patch.object(f1_account, "renew_with_session") as renew:
            _, _, action = live_token.renew(self.path)
        self.assertEqual(action, "kept")
        renew.assert_not_called()

    def test_renewal_window_constant_matches_a_day(self) -> None:
        self.assertEqual(live_token.RENEW_WINDOW, timedelta(hours=24))


if __name__ == "__main__":
    unittest.main()
