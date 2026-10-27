"""OpenAI-compatible client for Nebius Token Factory.

The hackathon scores runtime calls to Token Factory. Calling the same
Nemotron weights through another host does not qualify.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"


class TokenFactoryError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        super().__init__(f"Token Factory HTTP {status}: {detail}")


@dataclass(frozen=True)
class ChatResult:
    model: str
    content: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None


def load_dotenv(path: str) -> None:
    """Load KEY=VALUE lines into the environment. Existing vars win."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def api_key_from_env() -> str:
    key = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not key:
        raise TokenFactoryError(
            0,
            "NEBIUS_API_KEY is not set. Add it to hackathon/.env (see .env.example).",
        )
    return key


def base_url_from_env() -> str:
    return os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def chat(
    *,
    model: str,
    content: str,
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    max_tokens: int = 256,
    temperature: float = 0,
    timeout: float = 90,
) -> ChatResult:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        detail = detail.replace(api_key, "[redacted]")
        raise TokenFactoryError(exc.code, detail) from None
    except urllib.error.URLError as exc:
        raise TokenFactoryError(0, f"network error: {exc.reason}") from None
    latency_ms = int((time.monotonic() - started) * 1000)
    usage = payload.get("usage") or {}
    return ChatResult(
        model=str(payload.get("model") or model),
        content=message_text(payload),
        latency_ms=latency_ms,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )


def message_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise TokenFactoryError(200, "response had no choices")
    message = choices[0].get("message") or {}
    for field in ("content", "reasoning_content"):
        text = message.get(field)
        if isinstance(text, str) and text.strip():
            return text.strip()
    raise TokenFactoryError(200, "response message was empty")
