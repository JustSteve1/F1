# Jobs Admin v1 — Interval.ai telemetry pipeline

Private admin UI to **create / cancel / retry** FastF1 → BigQuery → Kaggle import jobs, with live step progress and failure logs.

| Layer | Store |
|-------|--------|
| Control plane (jobs, steps, %, logs) | **Postgres** (`DATABASE_URL`) |
| Data plane (telemetry / laps / sessions) | **BigQuery** (unchanged) |
| Worker | **Cloud Run Jobs** (on-demand) |
| Private gate | **Vercel Deployment Protection** |

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

Or apply manually:

```bash
psql "$DATABASE_URL" -f db/migrations/001_jobs.sql
```

### 2. App env

```bash
cp .env.example .env.local
# DATABASE_URL=postgresql://interval:interval@localhost:5432/interval_jobs
# JOB_WORKER_MODE=stub   # default — UI works without GCP/FastF1
```

### 3. Run Next.js

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000/admin/jobs](http://localhost:3000/admin/jobs).

With `JOB_WORKER_MODE=stub`, creating a job simulates the full step timeline so you can verify polling / cancel / retry without BigQuery.

### Local Python worker (optional)

```bash
cd worker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=...
export JOB_ID=<uuid>
# Dry-run without FastF1/BQ:
export WORKER_DRY_RUN=1
python entrypoint.py
```

Or set `JOB_WORKER_MODE=local` in the Next.js env so create/retry spawn `worker/entrypoint.py`.

## Enable Vercel Deployment Protection

v1 has **no public multi-user auth** for this admin surface. Lock the deployment:

1. Vercel → project (`f1-hazel-ten` / Interval.ai) → **Settings** → **Deployment Protection**
2. Enable **Vercel Authentication** (or Password Protection)
3. Restrict to your team / yourself
4. Optionally protect **Preview** and **Production**

After that, only authenticated Vercel users (or password holders) can reach `/admin/jobs`.

## Deploy Cloud Run Job

From `worker/`:

```bash
export PROJECT=f1-data-library
export REGION=europe-west1
export JOB=f1-telemetry-import

gcloud builds submit --tag gcr.io/$PROJECT/$JOB

gcloud run jobs create $JOB \
  --image gcr.io/$PROJECT/$JOB \
  --region $REGION \
  --service-account f1-jobs-runner@$PROJECT.iam.gserviceaccount.com \
  --set-env-vars "DATABASE_URL=...,BQ_PROJECT=$PROJECT,BQ_DATASET=f1_data_library_DS" \
  --max-retries 0 \
  --task-timeout 3600 \
  --memory 4Gi \
  --cpu 2
```

Update an existing job with `gcloud run jobs update …`.

### IAM

- **Worker SA**: BigQuery data Editor/JobUser on the dataset, Secret access for `DATABASE_URL` / Kaggle if used, Cloud SQL client if applicable.
- **Vercel / Next.js SA** (or workload identity): `roles/run.developer` (or custom) allowing `run.jobs.run` on the Cloud Run Job.
- On Vercel, set `GOOGLE_SERVICE_ACCOUNT_EMAIL` + private key JSON via env, **or** use Workload Identity Federation. The API uses Application Default Credentials via `google-auth-library`.

### App env on Vercel

```
DATABASE_URL=...
JOB_WORKER_MODE=cloud_run
GCP_PROJECT_ID=f1-data-library
CLOUD_RUN_REGION=europe-west1
CLOUD_RUN_JOB_NAME=f1-telemetry-import
# plus GCP credentials for the Next.js runtime
```

## First real job

1. Migrations applied; `JOB_WORKER_MODE=cloud_run` (prod) or `local`/`stub` (dev)
2. Open `/admin/jobs`
3. Create: year `2025`, race `Australian Grand Prix`, session `R`, include Kaggle as needed
4. Watch steps: queued → load_fastf1 → … → kaggle_upload → done
5. On failure, open detail logs; **Retry** clones params into a new job from the start

## Pipeline flags (UI ↔ CLI)

| UI toggle | CLI equivalent |
|-----------|----------------|
| No skip | `--no-skip` |
| Skip quality checks | `--skip-quality-checks` |
| Skip laps_unified | `--skip-unified` |
| Include Kaggle upload | runs `kaggle_upload.py` after import |

Source scripts live under `worker/pipeline/` (adapted from `JustSteve1/F1` `main` + `kaggle-upload`).
