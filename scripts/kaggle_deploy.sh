#!/usr/bin/env bash
# Incremental append: new BigQuery laps onto the live Kaggle dataset.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

exec python3 kaggle_upload.py deploy "$@"
