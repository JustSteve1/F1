# Interval.ai

Next.js product app for Interval.ai (F1 strategy / telemetry product).

**One trunk:** GitHub **`main`** is this Next.js app plus `worker/`. There is no separate `front-end` branch and no Python-only production `main`. Vercel **Production** must track `main`. Feature work (including MVP2) lands via PRs; Preview deploys those PRs.

The FastF1 → BigQuery worker lives under [`worker/`](./worker/). Do not add a repo-root `f1_telemetry_import.py` or an OpenF1 ingest path.

## Getting Started

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Jobs Admin (telemetry pipeline)

Private admin to run FastF1 → BigQuery → Kaggle import jobs with live progress.

- UI: [`/admin/jobs`](http://localhost:3000/admin/jobs)
- Setup, Postgres, Cloud Run Jobs, and Vercel: **[ADMIN_JOBS.md](./ADMIN_JOBS.md)**

```bash
docker compose up -d postgres
cp .env.example .env.local   # JOB_WORKER_MODE=stub for local UI only
pnpm dev
```

## Deploy on Vercel

| Target | Git ref | Role |
|--------|---------|------|
| **Production** | `main` | Live app. Set this in Vercel → Settings → Git → Production Branch. |
| **Preview** | PRs (e.g. `MVP2`) | Same env as Production for jobs (`JOB_WORKER_MODE=cloud_run`, JSON SA, `DATABASE_URL`). |

Enable **Deployment Protection** (see ADMIN_JOBS.md). Vercel has no Python: FastF1 schedule catalog is skipped (`VERCEL=1`). Seed FastF1 cache from a home/Mac IP with `gcloud storage rsync` (not `gsutil -m rsync`) and run the worker on Cloud Run — never on Vercel. The jobs form warns when GCS has no folder for the selected race.
