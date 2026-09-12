"""Unit tests for resample GCS checkpoint helpers (no live GCS)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import f1_telemetry_import as pipe  # noqa: E402


def test_staging_uri_uses_cache_bucket() -> None:
    with patch.dict(
        os.environ,
        {"FASTF1_CACHE_GCS_URI": "gs://f1-data-library-fastf1-cache/fastf1"},
        clear=False,
    ):
        uri = pipe._staging_parquet_uri("job-abc", "telemetry.parquet")
    assert uri == (
        "gs://f1-data-library-fastf1-cache/staging/job-abc/telemetry.parquet"
    )


def test_load_returns_none_when_missing() -> None:
    tel_blob = MagicMock()
    tel_blob.exists.return_value = False
    with patch.object(pipe, "_gcs_blob", return_value=(tel_blob, MagicMock())):
        assert pipe.load_resample_checkpoint("job-missing", log=lambda m: None) is None


def test_checkpoint_roundtrip_via_local_parquet(tmp_path: Path) -> None:
    telemetry = pd.DataFrame({"speed": [1.0, 2.0], "lap": [1, 1]})
    laps = pd.DataFrame({"lap_number": [1], "driver_number": ["44"]})
    uploaded: dict[str, Path] = {}

    class FakeBlob:
        def __init__(self, uri: str) -> None:
            self.uri = uri
            self.path = tmp_path / uri.replace("gs://bucket/", "")
            self.path.parent.mkdir(parents=True, exist_ok=True)

        def exists(self) -> bool:
            return self.path.exists()

        def upload_from_filename(self, filename: str) -> None:
            data = Path(filename).read_bytes()
            self.path.write_bytes(data)
            uploaded[self.uri] = self.path

        def download_to_filename(self, filename: str) -> None:
            Path(filename).write_bytes(self.path.read_bytes())

        def delete(self) -> None:
            if self.path.exists():
                self.path.unlink()

    blobs: dict[str, FakeBlob] = {}

    def fake_gcs(uri: str):
        blobs[uri] = blobs.get(uri) or FakeBlob(uri)
        return blobs[uri], MagicMock()

    class FakeStorageClient:
        def list_blobs(self, bucket, prefix):
            return [
                b
                for u, b in blobs.items()
                if u.startswith(f"gs://{bucket}/{prefix.rstrip('/')}")
                or prefix in u
            ]

    logs: list[str] = []
    with (
        patch.object(pipe, "_gcs_blob", side_effect=fake_gcs),
        patch.object(pipe, "_staging_parquet_uri") as uri_fn,
        patch("google.cloud.storage.Client", FakeStorageClient),
    ):

        def make_uri(_job_id: str, filename: str) -> str:
            return f"gs://bucket/staging/job-1/{filename}"

        uri_fn.side_effect = make_uri
        written = pipe.write_resample_checkpoint(
            "job-1", telemetry, laps, log=logs.append
        )
        assert written["telemetry_rows"] == 2
        assert any("Wrote resample checkpoint" in m for m in logs)

        loaded = pipe.load_resample_checkpoint("job-1", log=logs.append)
        assert loaded is not None
        tel_df, laps_df = loaded
        assert len(tel_df) == 2
        assert len(laps_df) == 1
        assert any("Using checkpoint from" in m for m in logs)

        deleted = pipe.delete_resample_checkpoint("job-1", log=logs.append)
        assert deleted == 2
        assert pipe.load_resample_checkpoint("job-1", log=lambda m: None) is None


if __name__ == "__main__":
    test_staging_uri_uses_cache_bucket()
    test_load_returns_none_when_missing()
    test_checkpoint_roundtrip_via_local_parquet(Path("/tmp/ckpt-test"))
    print("ok")
