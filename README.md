# Interval.ai

Next.js product app for Interval.ai (F1 strategy / telemetry product).

## Getting Started

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

## Jobs Admin (telemetry pipeline)

Private admin to run FastF1 → BigQuery → Kaggle import jobs with live progress.

- UI: [`/admin/jobs`](http://localhost:3000/admin/jobs)
- Setup, Postgres, Cloud Run Jobs, and Vercel Deployment Protection: see **[ADMIN_JOBS.md](./ADMIN_JOBS.md)**

```bash
docker compose up -d postgres
cp .env.example .env.local   # JOB_WORKER_MODE=stub for local UI
pnpm dev
```

## Deploy on Vercel

Deploy this Next.js app as usual. For the Jobs Admin, enable **Deployment Protection** (see ADMIN_JOBS.md) rather than building a public auth system for v1.
