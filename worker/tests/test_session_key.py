"""Dutch GP 2026 R session_key must stay 2456128946."""

from __future__ import annotations

import hashlib


def generate_session_key(year: int, race: str, session_type: str) -> int:
    key_str = f"{year}-{race}-{session_type}"
    return int(hashlib.md5(key_str.encode()).hexdigest()[:8], 16)


def test_dutch_r_session_key() -> None:
    assert generate_session_key(2026, "Dutch Grand Prix", "R") == 2456128946


def test_dutch_fp1_differs() -> None:
    assert generate_session_key(2026, "Dutch Grand Prix", "FP1") == 1804436140
    assert generate_session_key(2026, "Dutch Grand Prix", "FP1") != 2456128946


if __name__ == "__main__":
    test_dutch_r_session_key()
    test_dutch_fp1_differs()
    print("ok")
