import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from interval_agent.models import NANO, SUPER, model_for
from interval_agent.token_factory import (
    TokenFactoryError,
    api_key_from_env,
    chat,
    load_dotenv,
    message_text,
)


class ModelRolesTest(unittest.TestCase):
    def test_fast_and_plan_roles(self):
        self.assertEqual(model_for("format"), NANO)
        self.assertEqual(model_for("plan"), SUPER)

    def test_unknown_role(self):
        with self.assertRaises(ValueError):
            model_for("invent")


class MessageTextTest(unittest.TestCase):
    def test_content(self):
        payload = {"choices": [{"message": {"content": " ready "}}]}
        self.assertEqual(message_text(payload), "ready")

    def test_reasoning_fallback(self):
        payload = {
            "choices": [
                {"message": {"content": "", "reasoning_content": "thinking done"}}
            ]
        }
        self.assertEqual(message_text(payload), "thinking done")

    def test_empty(self):
        with self.assertRaises(TokenFactoryError):
            message_text({"choices": [{"message": {"content": "  "}}]})


class EnvTest(unittest.TestCase):
    def test_missing_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TokenFactoryError) as raised:
                api_key_from_env()
        self.assertNotIn("sk-", str(raised.exception))
        self.assertIn("NEBIUS_API_KEY", str(raised.exception))

    def test_dotenv_does_not_override(self):
        path = self._write_env("NEBIUS_API_KEY=from-file\nNEBIUS_BASE_URL=https://example.test/v1\n")
        with mock.patch.dict(os.environ, {"NEBIUS_API_KEY": "already"}, clear=True):
            load_dotenv(path)
            self.assertEqual(os.environ["NEBIUS_API_KEY"], "already")
            self.assertEqual(os.environ["NEBIUS_BASE_URL"], "https://example.test/v1")

    def _write_env(self, text: str) -> str:
        import tempfile

        handle = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        self.addCleanup(os.remove, handle.name)
        return handle.name


class ChatTest(unittest.TestCase):
    def test_posts_bearer_and_parses_usage(self):
        captured = {}

        class Response:
            status = 200

            def read(self):
                return json.dumps(
                    {
                        "model": NANO,
                        "choices": [{"message": {"content": "ready"}}],
                        "usage": {"prompt_tokens": 9, "completion_tokens": 1},
                    }
                ).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["auth"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data.decode())
            captured["timeout"] = timeout
            return Response()

        with mock.patch("interval_agent.token_factory.urllib.request.urlopen", fake_urlopen):
            result = chat(model=NANO, content="Reply with ready.", api_key="secret-key")

        self.assertEqual(result.content, "ready")
        self.assertEqual(result.prompt_tokens, 9)
        self.assertEqual(captured["auth"], "Bearer secret-key")
        self.assertTrue(captured["url"].endswith("/chat/completions"))
        self.assertEqual(captured["body"]["model"], NANO)
        self.assertNotIn("secret-key", json.dumps(captured["body"]))

    def test_http_error_redacts_key(self):
        def fake_urlopen(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"bad key secret-key"}'),
            )

        with mock.patch("interval_agent.token_factory.urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(TokenFactoryError) as raised:
                chat(model=NANO, content="hi", api_key="secret-key")
        self.assertEqual(raised.exception.status, 401)
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
