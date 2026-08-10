#!/usr/bin/env bash
# One-time: create FastF1 cache bucket + grant worker SA access.
set -euo pipefail

PROJECT="${PROJECT:-f1-data-library}"
BUCKET="${BUCKET:-f1-data-library-fastf1-cache}"
REGION="${REGION:-europe-west1}"
WORKER_SA="${WORKER_SA:-interval-jobs-worker@${PROJECT}.iam.gserviceaccount.com}"

if gsutil ls -b "gs://${BUCKET}" >/dev/null 2>&1; then
  echo "Bucket gs://${BUCKET} already exists"
else
  echo "Creating gs://${BUCKET} in ${REGION}…"
  gsutil mb -p "${PROJECT}" -l "${REGION}" -b on "gs://${BUCKET}"
fi

echo "Granting objectAdmin to ${WORKER_SA}…"
gsutil iam ch \
  "serviceAccount:${WORKER_SA}:roles/storage.objectAdmin" \
  "gs://${BUCKET}"

echo "Done. Set job env:"
echo "  FASTF1_CACHE_GCS_URI=gs://${BUCKET}/fastf1"
echo "  FASTF1_CACHE_DIR=/tmp/fastf1-cache"
