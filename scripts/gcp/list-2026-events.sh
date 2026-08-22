#!/usr/bin/env bash
# List stored 2026 F1 events from BigQuery (sessions table, telemetry fallback).
set -euo pipefail

PROJECT="${BQ_PROJECT:-f1-data-library}"
DATASET="${BQ_DATASET:-f1_data_library_DS}"
YEAR="${1:-2026}"
KEY_PATH="${GOOGLE_APPLICATION_CREDENTIALS:-/tmp/cursor-bq-reader-key.json}"

if [[ -n "${GOOGLE_SERVICE_ACCOUNT_KEY:-}" ]]; then
  KEY_PATH="/tmp/google-service-account-key.json"
  printf '%s' "$GOOGLE_SERVICE_ACCOUNT_KEY" > "$KEY_PATH"
  chmod 600 "$KEY_PATH"
elif [[ ! -f "$KEY_PATH" ]]; then
  echo "ERROR: No credentials found." >&2
  echo "Set GOOGLE_SERVICE_ACCOUNT_KEY or run provision-bq-reader-sa.sh first." >&2
  exit 1
fi

export GOOGLE_APPLICATION_CREDENTIALS="$KEY_PATH"

python3 - <<PY
import json
import os
import sys

from google.cloud import bigquery
from google.oauth2 import service_account

project = os.environ.get("BQ_PROJECT", "f1-data-library")
dataset = os.environ.get("BQ_DATASET", "f1_data_library_DS")
year = int("${YEAR}")
key_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

creds = service_account.Credentials.from_service_account_file(
    key_path,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
client = bigquery.Client(project=project, credentials=creds)

sessions_sql = f"""
SELECT DISTINCT
  season,
  event_name,
  session_type,
  session_name,
  circuit,
  location,
  country_name,
  date_start
FROM \`{project}.{dataset}.sessions\`
WHERE season = @year
ORDER BY event_name, session_type
"""

telemetry_sql = f"""
SELECT DISTINCT
  season,
  event_name,
  session_type
FROM \`{project}.{dataset}.telemetry\`
WHERE season = @year
ORDER BY event_name, session_type
"""

def run_query(sql):
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("year", "INT64", year)]
        ),
    )
    return list(job.result())

rows = run_query(sessions_sql)
source = "sessions"

if not rows:
    rows = run_query(telemetry_sql)
    source = "telemetry"

print(f"=== {year} events (from {source}) ===")
print(f"Distinct rows: {len(rows)}")
print()

if not rows:
    print("No stored events found for this season.")
    sys.exit(0)

# Group by event for readable output
by_event = {}
for row in rows:
    event = row["event_name"]
    session_type = row["session_type"]
    session_name = row.get("session_name") if hasattr(row, "get") else getattr(row, "session_name", None)
    label = session_name or session_type
    by_event.setdefault(event, []).append(
        {
            "session_type": session_type,
            "session_name": session_name,
            "label": label,
            "circuit": getattr(row, "circuit", None),
            "date_start": str(getattr(row, "date_start", None) or ""),
        }
    )

for event_name in sorted(by_event.keys()):
    sessions = by_event[event_name]
    circuit = next((s["circuit"] for s in sessions if s["circuit"]), "")
    header = event_name + (f" ({circuit})" if circuit else "")
    print(header)
    for s in sessions:
        extra = f" — {s['date_start']}" if s["date_start"] and s["date_start"] != "None" else ""
        print(f"  - {s['session_type']}: {s['label']}{extra}")
    print()

print(json.dumps({"year": year, "source": source, "event_count": len(by_event), "rows": len(rows)}, indent=2))
PY
