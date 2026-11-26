"""The interval bearer is handed to FastF1 without being printed."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1_auth  # noqa: E402


def _jwt(exp: float) -> str:
    encoded = jwt.encode({"exp": exp, "sub": "interval"}, "test", algorithm="HS256")
    return encoded if isinstance(encoded, str) else encoded.decode()


class ConfigureTests(unittest.TestCase):
    def tearDown(self) -> None:
        fastf1_auth.reset_fastf1_auth_status()

    def test_interval_token_is_stored_for_fastf1(self) -> None:
        token = _jwt(time.time() + 86_400)
        stored = MagicMock()
        manager = MagicMock()
        manager.store = stored
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f1-subscription-token"
            path.write_text(token)
            env = {
                "F1_SUBSCRIPTION_TOKEN_FILE": str(path),
                "F1_USERNAME": "",
                "F1_PASSWORD": "",
                "F1_EMAIL": "",
            }
            with (
                patch.dict(os.environ, env, clear=False),
                patch("fastf1.internals.f1account.token_manager", manager),
                patch("fastf1.set_auth_method") as set_method,
            ):
                status = fastf1_auth.configure_fastf1_auth()
        self.assertEqual(status, "token")
        self.assertEqual(stored.call_args.args[0].value, token)
        self.assertTrue(stored.call_args.args[0].authorization_header.startswith("Bearer "))
        set_method.assert_not_called()

    def test_password_env_selects_fastf1_password_sign_in(self) -> None:
        with (
            patch.dict(os.environ, {"F1_USERNAME": "driver@example.com", "F1_PASSWORD": "secret"}, clear=False),
            patch.object(fastf1_auth, "_read_token", return_value=None),
            patch("fastf1.set_auth_method") as set_method,
        ):
            status = fastf1_auth.configure_fastf1_auth()
        self.assertEqual(status, "password")
        set_method.assert_called_once_with("password")

    def test_missing_credentials_do_not_invent_a_token(self) -> None:
        with (
            patch.dict(os.environ, {"F1_USERNAME": "", "F1_PASSWORD": "", "F1_EMAIL": ""}, clear=False),
            patch.object(fastf1_auth, "_read_token", return_value=None),
            patch("fastf1.set_auth_method") as set_method,
        ):
            status = fastf1_auth.configure_fastf1_auth()
        self.assertEqual(status, "missing")
        set_method.assert_not_called()


if __name__ == "__main__":
    unittest.main()
