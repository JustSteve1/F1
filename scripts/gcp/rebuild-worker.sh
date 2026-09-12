#!/usr/bin/env bash
# Rebuild Cloud Run Job f1-telemetry-import from worker/ (lesson 5).
# Pins INGEST_SOURCE=fastf1 on the job. Task timeout 14400s (lesson 7).
#
# Usage (from repo root, branch MVP2):
#   ./scripts/gcp/rebuild-worker.sh
#
# Auth: gcloud user ADC, or GCP_DEPLOYER_SERVICE_ACCOUNT_KEY (full JSON).
set -euo pipefail

PROJECT="${GCP_PROJECT:-f1-data-library}"
REGION="${CLOUD_RUN_REGION:-europe-west1}"
JOB="${CLOUD_RUN_JOB_NAME:-f1-telemetry-import}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy/${JOB}:v1"
WORKER_SA="interval-jobs-worker@${PROJECT}.iam.gserviceaccount.com"
KEY_PATH="${GCP_DEPLOYER_KEY_PATH:-/tmp/gcp-deployer.json}"

cleanup() {
  if [[ -n "${GCP_DEPLOYER_SERVICE_ACCOUNT_KEY:-}" ]]; then
    rm -f "$KEY_PATH"
  fi
}
trap cleanup EXIT

if [[ -n "${GCP_DEPLOYER_SERVICE_ACCOUNT_KEY:-}" ]]; then
  printf '%s' "$GCP_DEPLOYER_SERVICE_ACCOUNT_KEY" > "$KEY_PATH"
  chmod 600 "$KEY_PATH"
  gcloud auth activate-service-account --key-file="$KEY_PATH" --quiet
fi

gcloud config set project "$PROJECT" --quiet

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "Building $IMAGE from $ROOT/worker …"
gcloud builds submit worker --project="$PROJECT" --tag="$IMAGE"

echo "Updating Cloud Run Job $JOB (INGEST_SOURCE=fastf1) …"
gcloud run jobs update "$JOB" \
  --project="$PROJECT" --region="$REGION" \
  --image="$IMAGE" \
  --service-account="$WORKER_SA" \
  --set-cloudsql-instances="$PROJECT:$REGION:interval-jobs" \
  --max-retries=0 --task-timeout=14400 --memory=4Gi --cpu=2 \
  --update-env-vars=INGEST_SOURCE=fastf1,FASTF1_CACHE_GCS_URI=gs://f1-data-library-fastf1-cache/fastf1,FASTF1_CACHE_DIR=/tmp/fastf1-cache

echo "Clearing WORKER_DRY_RUN if set …"
gcloud run jobs update "$JOB" \
  --project="$PROJECT" --region="$REGION" \
  --remove-env-vars=WORKER_DRY_RUN \
  && echo "Removed WORKER_DRY_RUN" \
  || echo "WORKER_DRY_RUN was not set (ok)"

echo "Verifying job image + INGEST_SOURCE …"
gcloud run jobs describe "$JOB" \
  --project="$PROJECT" --region="$REGION" \
  --format=json \
  | python3 -c '
import json, sys
job = json.load(sys.stdin)
# Cloud Run Jobs API shape varies slightly across gcloud versions.
def walk(obj, acc):
    if isinstance(obj, dict):
        if "image" in obj and "env" in obj:
            acc.append(obj)
        for v in obj.values():
            walk(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk(v, acc)
found = []
walk(job, found)
if not found:
    print("Could not find container spec; dumping spec keys")
    print(json.dumps(job.get("spec", {}), indent=2)[:2000])
    sys.exit(1)
c = found[0]
print("image:", c.get("image"))
env = {e.get("name"): e.get("value") for e in c.get("env") or []}
print("INGEST_SOURCE:", env.get("INGEST_SOURCE"))
print("WORKER_DRY_RUN:", env.get("WORKER_DRY_RUN", "<unset>"))
print("FASTF1_CACHE_GCS_URI:", env.get("FASTF1_CACHE_GCS_URI"))
if env.get("INGEST_SOURCE") != "fastf1":
    sys.exit("INGEST_SOURCE is not fastf1")
'
