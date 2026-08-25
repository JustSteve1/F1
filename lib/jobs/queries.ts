import { query } from "@/lib/db";
import type { JobDetail, JobLogRow, JobRow, JobStepRow } from "./types";
import {
  type JobParams,
  SESSION_TYPES,
  stepsForParams,
  type SessionType,
} from "./steps";

function mapJob(row: Record<string, unknown>): JobRow {
  return {
    id: String(row.id),
    status: row.status as JobRow["status"],
    params: row.params as JobParams,
    progress_pct: Number(row.progress_pct ?? 0),
    current_step: (row.current_step as string | null) ?? null,
    status_message: (row.status_message as string | null) ?? null,
    error: (row.error as string | null) ?? null,
    cloud_run_execution_name:
      (row.cloud_run_execution_name as string | null) ?? null,
    created_at: new Date(row.created_at as string).toISOString(),
    started_at: row.started_at
      ? new Date(row.started_at as string).toISOString()
      : null,
    finished_at: row.finished_at
      ? new Date(row.finished_at as string).toISOString()
      : null,
    updated_at: new Date(row.updated_at as string).toISOString(),
  };
}

export function parseJobParams(input: unknown): JobParams {
  if (!input || typeof input !== "object") {
    throw new Error("Invalid job params");
  }
  const body = input as Record<string, unknown>;

  const yearsRaw = body.years ?? body.year;
  const years = Array.isArray(yearsRaw)
    ? yearsRaw.map((y) => Number(y)).filter((y) => Number.isFinite(y))
    : typeof yearsRaw === "number"
      ? [yearsRaw]
      : typeof yearsRaw === "string"
        ? yearsRaw
            .split(/[,\s]+/)
            .map((y) => Number(y.trim()))
            .filter((y) => Number.isFinite(y))
        : [];

  if (!years.length) throw new Error("At least one year is required");

  const race = String(body.race ?? "").trim();
  if (!race) throw new Error("Race name is required");

  const sessionsRaw = body.sessions;
  const sessions = (
    Array.isArray(sessionsRaw)
      ? sessionsRaw.map(String)
      : typeof sessionsRaw === "string"
        ? sessionsRaw.split(/[,\s]+/)
        : ["R"]
  ).filter((s): s is SessionType =>
    (SESSION_TYPES as readonly string[]).includes(s),
  );

  if (!sessions.length) throw new Error("At least one session type is required");

  const uniqueSessions = [...new Set(sessions)];

  let sessionLabels: Record<string, string> | undefined;
  const labelsRaw = body.sessionLabels;
  if (labelsRaw && typeof labelsRaw === "object" && !Array.isArray(labelsRaw)) {
    const cleaned: Record<string, string> = {};
    for (const [code, label] of Object.entries(
      labelsRaw as Record<string, unknown>,
    )) {
      if (!uniqueSessions.includes(code as SessionType)) continue;
      if (typeof label === "string" && label.trim()) {
        cleaned[code] = label.trim();
      }
    }
    if (Object.keys(cleaned).length) sessionLabels = cleaned;
  }

  return {
    years: [...new Set(years)].sort(),
    race,
    sessions: uniqueSessions,
    ...(sessionLabels ? { sessionLabels } : {}),
    noSkip: Boolean(body.noSkip),
    skipQuality: Boolean(body.skipQuality),
    skipUnified: Boolean(body.skipUnified),
    includeKaggle: Boolean(body.includeKaggle),
  };
}

export async function createJob(params: JobParams): Promise<JobRow> {
  const { getPool } = await import("@/lib/db");
  const client = await getPool().connect();
  try {
    await client.query("BEGIN");
    const jobRes = await client.query(
      `INSERT INTO jobs (status, params, progress_pct, current_step, status_message)
       VALUES ('queued', $1::jsonb, 0, 'queued', 'Job queued')
       RETURNING *`,
      [JSON.stringify(params)],
    );
    const job = mapJob(jobRes.rows[0]);
    const steps = stepsForParams(params);

    for (const step of steps) {
      await client.query(
        `INSERT INTO job_steps (job_id, step_key, step_order, status, message)
         VALUES ($1, $2, $3, $4, $5)`,
        [
          job.id,
          step.key,
          step.order,
          step.key === "queued" ? "succeeded" : "pending",
          step.key === "queued" ? "Waiting for worker" : null,
        ],
      );
    }

    await client.query(
      `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'info', $2)`,
      [job.id, `Created job for ${params.race} (${params.years.join(", ")})`],
    );

    await client.query("COMMIT");
    return job;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export async function listJobs(limit = 50): Promise<JobRow[]> {
  const res = await query(
    `SELECT * FROM jobs ORDER BY created_at DESC LIMIT $1`,
    [limit],
  );
  return res.rows.map(mapJob);
}

export async function getJob(id: string): Promise<JobRow | null> {
  const res = await query(`SELECT * FROM jobs WHERE id = $1`, [id]);
  if (!res.rows[0]) return null;
  return mapJob(res.rows[0]);
}

export async function getJobDetail(
  id: string,
  logLimit = 200,
): Promise<JobDetail | null> {
  const job = await getJob(id);
  if (!job) return null;

  const stepsRes = await query(
    `SELECT * FROM job_steps WHERE job_id = $1 ORDER BY step_order ASC`,
    [id],
  );
  const logsRes = await query(
    `SELECT * FROM job_logs WHERE job_id = $1 ORDER BY ts DESC, id DESC LIMIT $2`,
    [id, logLimit],
  );

  const steps: JobStepRow[] = stepsRes.rows.map((row) => ({
    id: String(row.id),
    job_id: String(row.job_id),
    step_key: String(row.step_key),
    step_order: Number(row.step_order),
    status: row.status as JobStepRow["status"],
    message: (row.message as string | null) ?? null,
    started_at: row.started_at
      ? new Date(row.started_at as string).toISOString()
      : null,
    finished_at: row.finished_at
      ? new Date(row.finished_at as string).toISOString()
      : null,
  }));

  const logs: JobLogRow[] = logsRes.rows
    .map((row) => ({
      id: Number(row.id),
      job_id: String(row.job_id),
      ts: new Date(row.ts as string).toISOString(),
      level: String(row.level),
      message: String(row.message),
    }))
    .reverse();

  return { ...job, steps, logs };
}

export async function requestCancel(id: string): Promise<JobRow | null> {
  const res = await query(
    `UPDATE jobs
     SET status = 'cancelling',
         status_message = 'Cancel requested — worker will stop between steps',
         updated_at = now()
     WHERE id = $1 AND status IN ('queued', 'running')
     RETURNING *`,
    [id],
  );
  if (!res.rows[0]) return null;

  await query(
    `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'warn', $2)`,
    [id, "Cancel requested from admin UI"],
  );
  return mapJob(res.rows[0]);
}

export async function forceFailJob(
  id: string,
  reason: string,
): Promise<JobRow | null> {
  const res = await query(
    `UPDATE jobs
     SET status = 'failed',
         finished_at = COALESCE(finished_at, now()),
         error = $2,
         status_message = $2,
         updated_at = now()
     WHERE id = $1 AND status IN ('queued', 'running', 'cancelling')
     RETURNING *`,
    [id, reason],
  );
  if (!res.rows[0]) return null;

  await query(
    `UPDATE job_steps
     SET status = 'failed',
         finished_at = COALESCE(finished_at, now()),
         message = COALESCE(message, $2)
     WHERE job_id = $1 AND status IN ('pending', 'running')`,
    [id, reason],
  );
  await query(
    `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'error', $2)`,
    [id, reason],
  );
  return mapJob(res.rows[0]);
}

export async function setCloudRunExecution(
  id: string,
  executionName: string | null,
) {
  await query(
    `UPDATE jobs
     SET cloud_run_execution_name = $2,
         updated_at = now()
     WHERE id = $1`,
    [id, executionName],
  );
}

export async function appendJobLog(
  id: string,
  message: string,
  level: string = "info",
) {
  await query(
    `INSERT INTO job_logs (job_id, level, message) VALUES ($1, $2, $3)`,
    [id, level, message],
  );
}
