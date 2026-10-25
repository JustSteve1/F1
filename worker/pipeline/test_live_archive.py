"""Official archive lines split into a session clock and a payload."""

from __future__ import annotations

import base64
import json
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_archive  # noqa: E402


def _zipped(payload: dict) -> str:
    raw = json.dumps(payload).encode()
    return base64.b64encode(zlib.compress(raw)[2:-4]).decode()


class ArchiveParseTests(unittest.TestCase):
    def test_json_and_compressed_lines_keep_their_clock(self) -> None:
        car = _zipped({"Entries": []})
        text = (
            "\ufeff00:00:00.000{\"Name\":\"Practice 1\"}\r\n"
            f"00:00:08.041\"{car}\"\r\n"
        )
        records = live_archive.parse_stream(text)
        self.assertEqual(records[0][0], "00:00:00.000")
        self.assertEqual(records[0][1]["Name"], "Practice 1")
        self.assertEqual(records[1][0], "00:00:08.041")
        self.assertTrue(str(records[1][1]).startswith('"'))


if __name__ == "__main__":
    unittest.main()
