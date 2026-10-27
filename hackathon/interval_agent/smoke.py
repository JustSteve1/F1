"""Call Nano and Super on Token Factory and print timings.

Usage, from the hackathon directory:

    python3 -m interval_agent.smoke
    python3 -m interval_agent.smoke --with-ultra
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from interval_agent.models import SMOKE_MODELS, ULTRA
from interval_agent.token_factory import (
    TokenFactoryError,
    api_key_from_env,
    base_url_from_env,
    chat,
    load_dotenv,
)

PROMPT = "Reply with the single word ready."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-ultra",
        action="store_true",
        help="also call Nemotron 3 Ultra (higher price; off by default)",
    )
    args = parser.parse_args(argv)

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(str(env_path))

    try:
        api_key = api_key_from_env()
    except TokenFactoryError as exc:
        print(exc, file=sys.stderr)
        return 2

    models = list(SMOKE_MODELS)
    if args.with_ultra:
        models.append(ULTRA)

    base_url = base_url_from_env()
    print(f"base_url {base_url}")
    failed = False
    for model in models:
        try:
            result = chat(
                model=model,
                content=PROMPT,
                api_key=api_key,
                base_url=base_url,
            )
        except TokenFactoryError as exc:
            failed = True
            print(f"FAIL  {model}  {exc}")
            continue
        preview = " ".join(result.content.split())[:80]
        print(
            f"OK    {model}  {result.latency_ms}ms"
            f"  in={result.prompt_tokens} out={result.completion_tokens}"
            f"  {preview}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
