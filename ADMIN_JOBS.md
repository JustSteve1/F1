# Jobs Admin v1 — Interval.ai telemetry pipeline

Private admin UI to **create / cancel / retry** FastF1 → BigQuery → Kaggle import jobs, with live step progress and failure logs.

## One trunk

| Surface | What it is |
|---------|------------|
| GitHub **`main`** | This Next.js app + [`worker/`](./worker/). Production git ref. |
| Vercel **Production** | Must deploy **`main`** (Settings → Git → Production Branch). |
| Vercel **Preview** | PRs off `main` (e.g. `MVP2`). Same job env as Production. |
| Worker | Cloud Run Job `f1-telemetry-import`, built from `worker/`. Not Vercel. |
| FastF1 seed / catalog | Laptop (consumer IP) or Cloud Run. **Never Python on Vercel.** |

There is no `front-end` branch and no Python-only `main`. Legacy snapshots: tags `legacy-python-main` and `legacy-front-end`. Do not add a repo-root `f1_telemetry_import.py` or OpenF1 ingest.

Vercel Node has no FastF1. [`lib/jobs/import-catalog.ts`](./lib/jobs/import-catalog.ts) skips the Python schedule check when `VERCEL=1` (yellow banner on `/admin/jobs` is expected). Session codes are still validated in JS (`FP1/FP2/FP3/Q/SQ/S/R`).

| Layer | Store |
|-------|--------|
| Control plane (jobs, steps, %, logs) | **Postgres** (`DATABASE_URL`) — Cloud SQL `interval-jobs` |
| Data plane (telemetry / laps / sessions) | **BigQuery** `f1-data-library.f1_data_library_DS` |
| Worker | **Cloud Run Jobs** `f1-telemetry-import` (europe-west1) |
| Private gate | **Vercel Deployment Protection** |

## Live GCP setup (path B: Vercel + Cloud Run Jobs)

**Project:** `f1-data-library` · **Region:** `europe-west1`

### Resources (already provisioned)

| Resource | Name / value |
|----------|----------------|
| Cloud SQL (Postgres 16) | `interval-jobs` |
| Connection name | `f1-data-library:europe-west1:interval-jobs` |
| Public IP | `130.211.72.94` |
| Database | `interval_jobs` |
| DB user | `interval_jobs` |
| SSL | `ENCRYPTED_ONLY` |
| Trigger SA | `interval-jobs-trigger@f1-data-library.iam.gserviceaccount.com` |
| Worker SA | `interval-jobs-worker@f1-data-library.iam.gserviceaccount.com` |
| Trigger JSON key (local, **never commit**) | `~/.config/gcloud/interval-jobs-trigger.json` |
| Cloud Run Job | `f1-telemetry-import` |
| Image | `europe-west1-docker.pkg.dev/f1-data-library/cloud-run-source-deploy/f1-telemetry-import:v1` |

### Connectivity model (v1)

| Client | How it reaches Postgres |
|--------|-------------------------|
| **Cloud Run Job (worker)** | Cloud SQL Unix socket via `--set-cloudsql-instances` + `DATABASE_URL` with `host=/cloudsql/...` |
| **Next.js (local)** | Public IP + SSL; your IP must be in **Authorized networks** |
| **Next.js (Vercel)** | Public IP + SSL; Vercel egress IPs are **dynamic** — see below |

**Authorized networks today:** your admin IP only (`93.114.63.228/32` at provision time).

For Vercel preview/prod to reach Cloud SQL over public IP you must either:

1. Temporarily authorize `0.0.0.0/0` (works with SSL + strong password; **document the risk** — open to the internet on 5432), or
2. Re-authorize whenever your IP / testing needs change, or
3. Later: move Next.js control-plane access behind a connector/proxy.

```bash
# Add current public IP
MY_IP=$(curl -s https://ifconfig.me)
gcloud sql instances patch interval-jobs --project=f1-data-library \
  --authorized-networks="${MY_IP}/32" --quiet

# Temporary wide-open for preview testing (revert after)
gcloud sql instances patch interval-jobs --project=f1-data-library \
  --authorized-networks=0.0.0.0/0 --quiet
```

### IAM (worker / trigger)

- **Trigger SA:** `roles/run.developer` (execute Cloud Run Jobs)
- **Worker SA:** `roles/bigquery.jobUser`, `roles/bigquery.dataEditor`, `roles/cloudsql.client`
- **Worker SA (FastF1 cache):** `roles/storage.objectAdmin` on `gs://f1-data-library-fastf1-cache`
- **Worker SA (Kaggle secrets):** `roles/secretmanager.secretAccessor` on `kaggle-username` + `kaggle-key` (or `kaggle-api-token`)

### Kaggle credentials (Cloud Run)

`includeKaggle=true` needs Kaggle auth on job `f1-telemetry-import`. The worker accepts either:

| Preferred (configured) | Env | Secret Manager |
|-----------|-----|----------------|
| API token | `KAGGLE_API_TOKEN` | `kaggle-api-token` |
| Legacy (optional fallback) | `KAGGLE_USERNAME` + `KAGGLE_KEY` | `kaggle-username` + `kaggle-key` |

Also set plain env `KAGGLE_DATASET` (default `stevefza/f1-2026-bahrain-testing-day-2`).

**Current Cloud Run setup:** `KAGGLE_API_TOKEN` ← `kaggle-api-token:latest`. Upload uses **kagglehub** (`kagglehub.dataset_upload`).

**Generate credentials** at [https://www.kaggle.com/settings/api](https://www.kaggle.com/settings/api):

- **Preferred:** “Generate New Token” → copy token (do not commit it).
- **Legacy:** “Create Legacy API Key” → `kaggle.json` with `username` + `key` (or use `~/.kaggle/kaggle.json`).

**Preferred: mount `KAGGLE_API_TOKEN`**

```bash
export PROJECT=f1-data-library
export REGION=europe-west1
export JOB=f1-telemetry-import
export SA=interval-jobs-worker@$PROJECT.iam.gserviceaccount.com

# Paste token when prompted (or use --data-file=./token.txt then shred the file)
printf '%s' 'PASTE_TOKEN_HERE' | gcloud secrets create kaggle-api-token \
  --project=$PROJECT --replication-policy=automatic --data-file=-
# If secret already exists:
# printf '%s' 'PASTE_TOKEN_HERE' | gcloud secrets versions add kaggle-api-token \
#   --project=$PROJECT --data-file=-

gcloud secrets add-iam-policy-binding kaggle-api-token \
  --project=$PROJECT \
  --member="serviceAccount:$SA" \
  --role=roles/secretmanager.secretAccessor

gcloud run jobs update $JOB \
  --project=$PROJECT --region=$REGION \
  --update-secrets=KAGGLE_API_TOKEN=kaggle-api-token:latest \
  --update-env-vars=KAGGLE_DATASET=stevefza/f1-2026-bahrain-testing-day-2 \
  --remove-secrets=KAGGLE_USERNAME,KAGGLE_KEY
```

**Legacy (optional; previously used from local `~/.kaggle/kaggle.json`):**

```bash
export PROJECT=f1-data-library
export REGION=europe-west1
export JOB=f1-telemetry-import
export SA=interval-jobs-worker@$PROJECT.iam.gserviceaccount.com

# From ~/.kaggle/kaggle.json fields (do not echo values into shell history)
python3 - <<'PY'
import json, subprocess, tempfile, os
from pathlib import Path
cfg = json.loads(Path.home().joinpath(".kaggle/kaggle.json").read_text())
for name, field in (("kaggle-username", "username"), ("kaggle-key", "key")):
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        f.write(cfg[field].strip()); path = f.name
    try:
        r = subprocess.run(["gcloud", "secrets", "describe", name, f"--project={os.environ['PROJECT']}"], capture_output=True)
        cmd = ["gcloud", "secrets", "versions", "add", name, f"--project={os.environ['PROJECT']}", f"--data-file={path}"]
        if r.returncode != 0:
            cmd = ["gcloud", "secrets", "create", name, f"--project={os.environ['PROJECT']}", "--replication-policy=automatic", f"--data-file={path}"]
        subprocess.check_call(cmd)
    finally:
        os.unlink(path)
PY

for SECRET in kaggle-username kaggle-key; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --project=$PROJECT \
    --member="serviceAccount:$SA" \
    --role=roles/secretmanager.secretAccessor
done

gcloud run jobs update $JOB \
  --project=$PROJECT --region=$REGION \
  --update-secrets=KAGGLE_USERNAME=kaggle-username:latest,KAGGLE_KEY=kaggle-key:latest \
  --update-env-vars=KAGGLE_DATASET=stevefza/f1-2026-bahrain-testing-day-2
```

Never commit `kaggle.json`, tokens, or secret values.

### FastF1 GCS cache (Cloud Run)

Cloud Run often soft-fails livetiming downloads (`Failed to load timing data` → `DataNotLoadedError` on `.laps`). The worker pulls/pushes a shared FastF1 cache from GCS so seeded sessions work offline of the livetiming API.

| Item | Value |
|------|--------|
| Bucket | `gs://f1-data-library-fastf1-cache` (`europe-west1`) |
| Prefix | `fastf1/` |
| Job env | `FASTF1_CACHE_GCS_URI=gs://f1-data-library-fastf1-cache/fastf1` |
| Local cache | `FASTF1_CACHE_DIR=/tmp/fastf1-cache` (Cloud Run) / `~/.cache/fastf1` (laptop) |

**Create bucket + IAM (once):**

```bash
gsutil mb -p f1-data-library -l europe-west1 -b on gs://f1-data-library-fastf1-cache
gsutil iam ch \
  serviceAccount:interval-jobs-worker@f1-data-library.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://f1-data-library-fastf1-cache
```

**Seed cache from a home/consumer IP** (F1 livetiming blocks Cloud Run, Colab, and other datacenter IPs):

```bash
export FASTF1_CACHE_GCS_URI=gs://f1-data-library-fastf1-cache/fastf1
python3 worker/pipeline/seed_fastf1_cache.py \
  --year 2026 --race "Monaco Grand Prix" --session Q R

# Upload (macOS: use gcloud storage, not gsutil -m — sys.maxint):
gcloud storage rsync --recursive ~/.cache/fastf1 gs://f1-data-library-fastf1-cache/fastf1
```

### Rebuild / update the worker image

```bash
export PROJECT=f1-data-library
export REGION=europe-west1
export JOB=f1-telemetry-import
export IMAGE=$REGION-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/$JOB:v1

gcloud builds submit worker --project=$PROJECT --tag=$IMAGE

gcloud run jobs update $JOB \
  --project=$PROJECT --region=$REGION \
  --image=$IMAGE \
  --service-account=interval-jobs-worker@$PROJECT.iam.gserviceaccount.com \
  --set-cloudsql-instances=$PROJECT:$REGION:interval-jobs \
  --max-retries=0 --task-timeout=3600 --memory=4Gi --cpu=2 \
  --update-env-vars=FASTF1_CACHE_GCS_URI=gs://f1-data-library-fastf1-cache/fastf1,FASTF1_CACHE_DIR=/tmp/fastf1-cache
```

Clear dry-run when ready for real imports:

```bash
gcloud run jobs update f1-telemetry-import \
  --project=f1-data-library --region=europe-west1 \
  --remove-env-vars=WORKER_DRY_RUN
# or set WORKER_DRY_RUN=0
```

## Routes

| Path | Purpose |
|------|---------|
| `/admin/jobs` | Create job + live list |
| `/admin/jobs/[id]` | Detail: step timeline, %, scrolling logs, cancel/retry |
| `POST /api/admin/jobs` | Create + trigger worker |
| `GET /api/admin/jobs` | List |
| `GET /api/admin/jobs/[id]` | Detail (+ steps + recent logs) |
| `POST /api/admin/jobs/[id]/cancel` | Set `cancelling` (worker stops between steps) |
| `POST /api/admin/jobs/[id]/fail` | Force-fail `queued` / `running` / `cancelling` (zombies) |
| `POST /api/admin/jobs/[id]/retry` | Clone params → new job + trigger |
| `POST /api/admin/import/load` | Load-focused create + trigger (FastF1 → BQ) |
| `GET /api/admin/import/status` | BQ presence + row counts for a race |

## Session Load API

Thin HTTP wrappers around the existing job pipeline — same BigQuery schema, async via Cloud Run.

### `POST /api/admin/import/load`

Creates a job and triggers the worker. Accepts singular `year` or `years` array:

```json
{
  "year": 2026,
  "race": "Dutch Grand Prix",
  "sessions": ["FP1"],
  "noSkip": false,
  "skipQuality": false,
  "skipUnified": false,
  "includeKaggle": false
}
```

**Response `201`:**

```json
{
  "jobId": "uuid",
  "status": "queued",
  "pollUrl": "/api/admin/jobs/{id}",
  "expectedTables": ["sessions", "laps", "telemetry", "laps_unified"],
  "sessionKeys": [{ "year": 2026, "race": "Dutch Grand Prix", "session": "FP1", "sessionKey": 1234567890 }]
}
```

Poll `GET /api/admin/jobs/{jobId}` until `status` is `succeeded` or `failed`.

### `GET /api/admin/import/status`

Read-only BigQuery check for what is already stored:

```
GET /api/admin/import/status?year=2026&race=Dutch%20Grand%20Prix
GET /api/admin/import/status?year=2026&race=Dutch%20Grand%20Prix&sessions=FP1,SQ,S,Q,R
```

**Response `200`:**

```json
{
  "year": 2026,
  "race": "Dutch Grand Prix",
  "sessionsInBigQuery": ["FP1"],
  "missingFromRequest": ["SQ", "S", "Q", "R"],
  "telemetryRows": 12345,
  "lapsRows": 693
}
```

Uses the same read credentials as the import catalog (`GOOGLE_SERVICE_ACCOUNT_KEY` or ADC).

### Dutch Grand Prix 2026 (sprint weekend)

FastF1 event name: **`Dutch Grand Prix`**. Sprint-format sessions: **`FP1`, `SQ`, `S`, `Q`, `R`** (no FP2/FP3).

**End-to-end load (after Mac seed → GCS):**

```bash
# 1. Seed on a home IP, then:
gcloud storage rsync --recursive ~/.cache/fastf1 gs://f1-data-library-fastf1-cache/fastf1

# 2. Trigger load (Production = main; Preview = PR)
curl -X POST "https://<host>/api/admin/import/load" \
  -H "Content-Type: application/json" \
  -d '{"year":2026,"race":"Dutch Grand Prix","sessions":["FP1"]}'

# 3. Poll job
curl "https://<host>/api/admin/jobs/{jobId}"

# 4. Verify BQ presence
curl "https://<host>/api/admin/import/status?year=2026&race=Dutch%20Grand%20Prix"
```

If GCS cache is missing for the race, the worker fails fast: seed with `worker/pipeline/seed_fastf1_cache.py` from a consumer IP, then `gcloud storage rsync`. Do not retry livetiming from Cloud Run or Colab.

## Local development

### 1. Postgres

```bash
docker compose up -d postgres
# applies db/migrations/001_jobs.sql on first boot
```

Or against Cloud SQL (SSL + authorized IP):

```bash
psql "$DATABASE_URL" -f db/migrations/001_jobs.sql
```

### 2. App env

```bash
cp .env.example .env.local
# Keep Firebase vars; add jobs block (see below)
```

**Local cloud_run mode (already merged into `.env.local` on the provisioned machine):**

```
DATABASE_URL=postgresql://interval_jobs:***@130.211.72.94:5432/interval_jobs?sslmode=require
JOB_WORKER_MODE=cloud_run
GCP_PROJECT_ID=f1-data-library
CLOUD_RUN_REGION=europe-west1
CLOUD_RUN_JOB_NAME=f1-telemetry-import
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/interval-jobs-trigger.json
BQ_PROJECT=f1-data-library
BQ_DATASET=f1_data_library_DS
```

Passwords / full URL live outside the repo:

- `~/.config/gcloud/interval-jobs-database-url.txt`
- `~/.config/gcloud/interval-jobs-app-pass.txt`
- `~/.config/gcloud/interval-jobs-trigger.json`

### 3. Run Next.js

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000/admin/jobs](http://localhost:3000/admin/jobs).

With `JOB_WORKER_MODE=stub`, creating a job simulates the full step timeline so you can verify polling / cancel / retry without BigQuery.

## Deploy: Production (`main`) + Preview (PRs)

v1 has **no public multi-user auth** for this admin surface. Lock deployments:

1. Vercel → **Settings → Git → Production Branch = `main`**
2. Open a PR into `main` (working branch **`MVP2`**) for Preview
3. Vercel → **Settings → Deployment Protection**
4. Enable **Vercel Authentication** (or Password Protection) for Preview **and** Production
5. Restrict to your team / yourself

### Required env: Preview **and** Production

Set the **same** keys on both environments. Stub mode on Production/Preview looks like a successful load but never writes BigQuery.

| Key | Value / notes |
|-----|----------------|
| `DATABASE_URL` | Cloud SQL public URL with `?sslmode=require` |
| `JOB_WORKER_MODE` | **`cloud_run`** (not `stub`) |
| `GCP_PROJECT_ID` | `f1-data-library` |
| `CLOUD_RUN_REGION` | `europe-west1` |
| `CLOUD_RUN_JOB_NAME` | `f1-telemetry-import` |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Full trigger-SA JSON as **one line** (not a file path) |
| `BQ_PROJECT` | `f1-data-library` |
| `BQ_DATASET` | `f1_data_library_DS` |
| `INGEST_SOURCE` | `fastf1` |
| Firebase `NEXT_PUBLIC_*` | Same as the product app |

`GOOGLE_APPLICATION_CREDENTIALS` (file path) and `WORKER_PYTHON` do **not** work on Vercel. FastF1 catalog is skipped when `VERCEL=1`. Session codes remain `FP1/FP2/FP3/Q/SQ/S/R`.

Also authorize Vercel egress (see connectivity) before Preview or Production can talk to Cloud SQL.

**Checklist before treating a deploy as real:**

- [ ] GitHub default branch is `main` (Next.js tree, not the old Python tag)
- [ ] Vercel Production Branch is `main`
- [ ] Preview and Production both have `JOB_WORKER_MODE=cloud_run`
- [ ] `GOOGLE_SERVICE_ACCOUNT_KEY` is JSON, not a path
- [ ] `DATABASE_URL` with `sslmode=require` on both
- [ ] `GCP_PROJECT_ID` / `CLOUD_RUN_JOB_NAME` set on both
- [ ] Creating a job logs `Triggered Cloud Run Job execution` (not stub)

## First real job (Monaco)

**Do not run against prod BQ until dry-run smoke is green and `WORKER_DRY_RUN` is cleared on the Cloud Run Job.**

1. Confirm Cloud Run Job exists; dry-run execution succeeds
2. `gcloud run jobs update … --remove-env-vars=WORKER_DRY_RUN`
3. Open `/admin/jobs` (Production `main`, Preview PR, or local with `JOB_WORKER_MODE=cloud_run`)
4. Create:
   - year: `2026`
   - race: `Monaco Grand Prix`
   - session: `R`
   - no-skip: **off**
   - quality + unified: **on**
   - includeKaggle: **false**
5. Watch steps → BigQuery tables in `f1_data_library_DS`
6. On failure, open detail logs; **Retry** clones params into a new job

## Smoke checks

```bash
# Cloud SQL reachable + schema
python3 - <<'PY'
# or: psql "$DATABASE_URL" -c '\dt'
PY

# Job exists
gcloud run jobs describe f1-telemetry-import \
  --project=f1-data-library --region=europe-west1

# Dry-run worker (JOB currently has WORKER_DRY_RUN=1)
# Insert a queued job via admin UI, or execute with JOB_ID override after creating a row.

# Next.js can obtain a trigger token (local):
# With .env.local loaded, creating a job in the UI should call run.googleapis.com
```

## Pipeline flags (UI ↔ CLI)

| UI toggle | CLI equivalent |
|-----------|----------------|
| No skip | `--no-skip` |
| Skip quality checks | `--skip-quality-checks` |
| Skip laps_unified | `--skip-unified` |
| Include Kaggle upload | runs `kaggle_upload.py` after import |

Source scripts live under `worker/pipeline/` only.
