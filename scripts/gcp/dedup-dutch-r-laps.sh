#!/usr/bin/env bash
# Preview or apply Dutch GP 2026 R laps dedup in BigQuery.
# session_key = 2456128946. Requires gcloud/bq auth (your Mac ADC is enough).
#
#   ./scripts/gcp/dedup-dutch-r-laps.sh           # counts only
#   ./scripts/gcp/dedup-dutch-r-laps.sh --apply   # delete extra lap copies
set -euo pipefail

PROJECT="${BQ_PROJECT:-f1-data-library}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

if ! command -v bq >/dev/null 2>&1; then
  echo "bq is required (Google Cloud SDK). You already used gcloud for Cloud Run." >&2
  echo "If bq is missing: gcloud components install bq" >&2
  exit 1
fi

if [[ "$APPLY" -eq 0 ]]; then
  echo "Preview Dutch R laps (session_key=2456128946) — no writes"
  bq query \
    --project_id="$PROJECT" \
    --use_legacy_sql=false \
    --nouse_cache \
    --format=pretty \
    < "$ROOT/sql/preview_dutch_2026_r.sql"
  echo
  echo "If extra_copies > 0, apply with:"
  echo "  ./scripts/gcp/dedup-dutch-r-laps.sh --apply"
  exit 0
fi

echo "Applying Dutch R laps dedup (session_key=2456128946)"
bq query \
  --project_id="$PROJECT" \
  --use_legacy_sql=false \
  --nouse_cache \
  --format=pretty \
  < "$ROOT/sql/dedup_dutch_2026_r_laps.sql"
echo
echo "Done. after.extra_copies should be 0 and laps_rows should equal unique_driver_laps."
echo "Do not load Dutch R until that is true."
