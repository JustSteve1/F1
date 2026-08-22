#!/usr/bin/env bash
# Provision read-only BigQuery service account for Cursor Cloud Agents.
# Requires GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY (admin-capable JSON) in the environment.
set -euo pipefail

PROJECT="${GCP_PROJECT:-f1-data-library}"
DATASET="${BQ_DATASET:-f1_data_library_DS}"
SA_ID="${GCP_READER_SA_ID:-cursor-bq-reader}"
SA_EMAIL="${SA_ID}@${PROJECT}.iam.gserviceaccount.com"
KEY_PATH="${GCP_READER_KEY_PATH:-/tmp/cursor-bq-reader-key.json}"
BOOTSTRAP_PATH="${GCP_BOOTSTRAP_KEY_PATH:-/tmp/gcp-bootstrap.json}"

cleanup() {
  rm -f "$BOOTSTRAP_PATH"
}
trap cleanup EXIT

if [[ -z "${GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY:-}" ]]; then
  echo "ERROR: GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY is not set." >&2
  echo "Add an admin-capable service account JSON to your Cloud Agent secrets." >&2
  exit 1
fi

printf '%s' "$GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY" > "$BOOTSTRAP_PATH"
chmod 600 "$BOOTSTRAP_PATH"
export GOOGLE_APPLICATION_CREDENTIALS="$BOOTSTRAP_PATH"

gcloud auth activate-service-account --key-file="$BOOTSTRAP_PATH" --quiet
gcloud config set project "$PROJECT" --quiet

echo "Project: $PROJECT"
echo "Dataset: $DATASET"
echo "Service account: $SA_EMAIL"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT" >/dev/null 2>&1; then
  echo "Service account already exists."
else
  echo "Creating service account..."
  gcloud iam service-accounts create "$SA_ID" \
    --project="$PROJECT" \
    --display-name="Cursor Cloud Agent BigQuery reader"
fi

echo "Binding roles/bigquery.jobUser at project level..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.jobUser" \
  --condition=None \
  --quiet >/dev/null

echo "Binding roles/bigquery.dataViewer on dataset ${DATASET}..."
gcloud bigquery datasets add-iam-policy-binding "$DATASET" \
  --project="$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/bigquery.dataViewer" \
  --condition=None \
  --quiet >/dev/null

if [[ -s "$KEY_PATH" ]]; then
  echo "Key file already exists at $KEY_PATH (skipping key creation)."
else
  echo "Creating service account key..."
  gcloud iam service-accounts keys create "$KEY_PATH" \
    --iam-account="$SA_EMAIL" \
    --project="$PROJECT" \
    --quiet
  chmod 600 "$KEY_PATH"
fi

# Safe summary only — never print key material
KEY_BYTES=$(wc -c < "$KEY_PATH" | tr -d ' ')
KEY_SHA=$(sha256sum "$KEY_PATH" | awk '{print $1}')
echo ""
echo "Provisioning complete."
echo "  SA email:    $SA_EMAIL"
echo "  Key path:    $KEY_PATH"
echo "  Key size:    ${KEY_BYTES} bytes"
echo "  Key SHA256:  ${KEY_SHA}"
echo ""
echo "Add the contents of $KEY_PATH to Cloud Agent secret GOOGLE_SERVICE_ACCOUNT_KEY."
