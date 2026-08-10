"""Sync FastF1 cache to/from GCS for Cloud Run workers.

Env:
  FASTF1_CACHE_GCS_URI  e.g. gs://f1-data-library-fastf1-cache/fastf1
  FASTF1_CACHE_DIR      local cache directory (default /tmp/fastf1-cache)
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    """Return (bucket, prefix) from gs://bucket/prefix."""
    raw = uri.strip()
    if not raw.startswith("gs://"):
        raise ValueError(f"FASTF1_CACHE_GCS_URI must start with gs:// (got {uri!r})")
    parsed = urlparse(raw)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"
    if not bucket:
        raise ValueError(f"Invalid GCS URI: {uri!r}")
    return bucket, prefix


def gcs_uri_configured() -> str | None:
    uri = os.environ.get("FASTF1_CACHE_GCS_URI", "").strip()
    return uri or None


def pull_cache(local_dir: str | None = None, log=print) -> dict:
    """Download cache objects from GCS into local_dir. No-op if URI unset."""
    uri = gcs_uri_configured()
    if not uri:
        log("FastF1 GCS cache: FASTF1_CACHE_GCS_URI unset — skip pull")
        return {"skipped": True, "pulled": 0}

    local = Path(
        local_dir
        or os.environ.get("FASTF1_CACHE_DIR", "/tmp/fastf1-cache")
    )
    local.mkdir(parents=True, exist_ok=True)

    from google.cloud import storage

    bucket_name, prefix = _parse_gcs_uri(uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(client.list_blobs(bucket_name, prefix=prefix))
    pulled = 0
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        rel = blob.name[len(prefix) :] if prefix else blob.name
        if not rel:
            continue
        dest = local / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        pulled += 1

    log(f"FastF1 GCS cache: pulled {pulled} file(s) from {uri} → {local}")
    return {"skipped": False, "pulled": pulled, "uri": uri, "local": str(local)}


def push_cache(local_dir: str | None = None, log=print) -> dict:
    """Upload local cache files to GCS. No-op if URI unset."""
    uri = gcs_uri_configured()
    if not uri:
        log("FastF1 GCS cache: FASTF1_CACHE_GCS_URI unset — skip push")
        return {"skipped": True, "pushed": 0}

    local = Path(
        local_dir
        or os.environ.get("FASTF1_CACHE_DIR", "/tmp/fastf1-cache")
    )
    if not local.exists():
        log(f"FastF1 GCS cache: local dir missing ({local}) — skip push")
        return {"skipped": True, "pushed": 0}

    from google.cloud import storage

    bucket_name, prefix = _parse_gcs_uri(uri)
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    pushed = 0
    for path in local.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(local).as_posix()
        blob_name = f"{prefix}{rel}"
        blob = bucket.blob(blob_name)
        # Skip upload if remote exists with same size (cheap idempotency)
        if blob.exists():
            blob.reload()
            if blob.size == path.stat().st_size:
                continue
        blob.upload_from_filename(str(path))
        pushed += 1

    log(f"FastF1 GCS cache: pushed {pushed} file(s) → {uri}")
    return {"skipped": False, "pushed": pushed, "uri": uri, "local": str(local)}
