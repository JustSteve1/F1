# Jobs Admin v1 — Interval.ai telemetry pipeline

Private admin UI to **create / cancel / retry** FastF1 → BigQuery → Kaggle import jobs, with live step progress and failure logs.

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
- Kaggle credentials: **not configured** (leave `includeKaggle=false`)

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
  --max-retries=0 --task-timeout=3600 --memory=4Gi --cpu=2
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
| `POST /api/admin/jobs/[id]/retry` | Clone params → new job + trigger |

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

## Deploy preview + Deployment Protection

v1 has **no public multi-user auth** for this admin surface. Lock the deployment:

1. Push / open a PR from `feature/jobs-admin-v1` (or deploy the branch in Vercel)
2. Vercel → project → **Deployments** → promote / open the **Preview** URL for this branch
3. Vercel → **Settings** → **Deployment Protection**
4. Enable **Vercel Authentication** (or Password Protection)
5. Restrict to your team / yourself
6. Protect **Preview** (and Production when you promote)

### Vercel env vars to set (Preview)

| Key | Notes |
|-----|--------|
| `DATABASE_URL` | Cloud SQL public URL with `?sslmode=require` (from `interval-jobs-database-url.txt`) |
| `JOB_WORKER_MODE` | `cloud_run` |
| `GCP_PROJECT_ID` | `f1-data-library` |
| `CLOUD_RUN_REGION` | `europe-west1` |
| `CLOUD_RUN_JOB_NAME` | `f1-telemetry-import` |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Full JSON of `~/.config/gcloud/interval-jobs-trigger.json` as one line |
| Firebase `NEXT_PUBLIC_*` | Same as today |

`GOOGLE_APPLICATION_CREDENTIALS` (file path) does **not** work on Vercel — use `GOOGLE_SERVICE_ACCOUNT_KEY` (or email + `GOOGLE_PRIVATE_KEY`).

Also authorize Vercel egress (see connectivity section) before preview can talk to Cloud SQL.

## First real job (Monaco)

**Do not run against prod BQ until dry-run smoke is green and `WORKER_DRY_RUN` is cleared on the Cloud Run Job.**

1. Confirm Cloud Run Job exists; dry-run execution succeeds
2. `gcloud run jobs update … --remove-env-vars=WORKER_DRY_RUN`
3. Open `/admin/jobs` (preview or local with `JOB_WORKER_MODE=cloud_run`)
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

Source scripts live under `worker/pipeline/` (adapted from `JustSteve1/F1` `main` + `kaggle-upload`).
