-- Jobs Admin v1 — control-plane state (Postgres)
-- BigQuery remains the data plane for telemetry / laps / sessions.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM (
    'queued',
    'running',
    'cancelling',
    'cancelled',
    'succeeded',
    'failed'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE job_step_status AS ENUM (
    'pending',
    'running',
    'succeeded',
    'failed',
    'skipped',
    'cancelled'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS jobs (
  id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  status                      job_status NOT NULL DEFAULT 'queued',
  params                      JSONB NOT NULL DEFAULT '{}'::jsonb,
  progress_pct                NUMERIC(5,2) NOT NULL DEFAULT 0,
  current_step                TEXT,
  status_message              TEXT,
  error                       TEXT,
  cloud_run_execution_name    TEXT,
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at                  TIMESTAMPTZ,
  finished_at                 TIMESTAMPTZ,
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_status_created_idx ON jobs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS jobs_created_idx ON jobs (created_at DESC);

CREATE TABLE IF NOT EXISTS job_steps (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id       UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  step_key     TEXT NOT NULL,
  step_order   INT NOT NULL,
  status       job_step_status NOT NULL DEFAULT 'pending',
  message      TEXT,
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ,
  UNIQUE (job_id, step_key)
);

CREATE INDEX IF NOT EXISTS job_steps_job_id_idx ON job_steps (job_id, step_order);

CREATE TABLE IF NOT EXISTS job_logs (
  id       BIGSERIAL PRIMARY KEY,
  job_id   UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  ts       TIMESTAMPTZ NOT NULL DEFAULT now(),
  level    TEXT NOT NULL DEFAULT 'info',
  message  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS job_logs_job_id_ts_idx ON job_logs (job_id, ts DESC);
