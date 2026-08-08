import { GoogleAuth, type JWTInput } from "google-auth-library";
import { appendJobLog, setCloudRunExecution } from "./queries";

export type WorkerMode = "cloud_run" | "stub" | "local";

export function getWorkerMode(): WorkerMode {
  const mode = (process.env.JOB_WORKER_MODE || "stub").toLowerCase();
  if (mode === "cloud_run" || mode === "local" || mode === "stub") return mode;
  return "stub";
}

/**
 * Resolve GCP credentials for Cloud Run Jobs triggers.
 *
 * Priority:
 * 1. GOOGLE_SERVICE_ACCOUNT_KEY — full JSON key string (Vercel-friendly)
 * 2. GOOGLE_SERVICE_ACCOUNT_EMAIL + GOOGLE_PRIVATE_KEY — split env vars
 * 3. GOOGLE_APPLICATION_CREDENTIALS / ADC — local path or ambient credentials
 */
function getGoogleAuth(): GoogleAuth {
  const scopes = ["https://www.googleapis.com/auth/cloud-platform"];
  const keyJson = process.env.GOOGLE_SERVICE_ACCOUNT_KEY?.trim();
  if (keyJson) {
    let credentials: JWTInput;
    try {
      credentials = JSON.parse(keyJson) as JWTInput;
    } catch {
      throw new Error("GOOGLE_SERVICE_ACCOUNT_KEY must be valid JSON");
    }
    return new GoogleAuth({ credentials, scopes });
  }

  const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL?.trim();
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  if (email && privateKey) {
    return new GoogleAuth({
      credentials: {
        client_email: email,
        private_key: privateKey,
      },
      scopes,
    });
  }

  // Falls back to GOOGLE_APPLICATION_CREDENTIALS path or ambient ADC.
  return new GoogleAuth({ scopes });
}

/**
 * Trigger the Cloud Run Job execution for a queued job.
 * Uses JSON key env vars (Vercel) or ADC / key file (local).
 */
export async function triggerCloudRunJob(jobId: string): Promise<string> {
  const project = process.env.GCP_PROJECT_ID;
  const region = process.env.CLOUD_RUN_REGION || "europe-west1";
  const jobName = process.env.CLOUD_RUN_JOB_NAME || "f1-telemetry-import";

  if (!project) {
    throw new Error("GCP_PROJECT_ID is required for cloud_run worker mode");
  }

  const auth = getGoogleAuth();
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  if (!token.token) {
    throw new Error("Failed to obtain GCP access token for Cloud Run Jobs");
  }

  const parent = `projects/${project}/locations/${region}/jobs/${jobName}`;
  const url = `https://run.googleapis.com/v2/${parent}:run`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token.token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      overrides: {
        containerOverrides: [
          {
            env: [{ name: "JOB_ID", value: jobId }],
          },
        ],
      },
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Cloud Run Jobs execute failed (${res.status}): ${text}`);
  }

  const data = (await res.json()) as { name?: string; metadata?: { name?: string } };
  const executionName = data.name || data.metadata?.name || `${parent}/executions/unknown`;
  await setCloudRunExecution(jobId, executionName);
  await appendJobLog(jobId, `Triggered Cloud Run Job execution: ${executionName}`);
  return executionName;
}

/**
 * Local stub: advances job steps in-process so the admin UI can be developed
 * without Cloud Run / BigQuery credentials.
 */
export async function triggerStubWorker(jobId: string): Promise<void> {
  await appendJobLog(jobId, "Stub worker started (JOB_WORKER_MODE=stub)");
  await setCloudRunExecution(jobId, `stub://${jobId}`);

  // Fire-and-forget simulated progress. Safe for local/dev only.
  void runStubProgress(jobId);
}

async function runStubProgress(jobId: string) {
  const { getPool } = await import("@/lib/db");
  const { progressForStep, stepsForParams } = await import("./steps");
  const pool = getPool();

  try {
    const jobRes = await pool.query(`SELECT * FROM jobs WHERE id = $1`, [jobId]);
    const job = jobRes.rows[0];
    if (!job) return;

    const params = job.params;
    const steps = stepsForParams(params).filter((s) => s.key !== "queued");

    await pool.query(
      `UPDATE jobs
       SET status = 'running', started_at = COALESCE(started_at, now()),
           status_message = 'Stub worker running', updated_at = now()
       WHERE id = $1`,
      [jobId],
    );

    for (const step of steps) {
      const statusRes = await pool.query(
        `SELECT status FROM jobs WHERE id = $1`,
        [jobId],
      );
      const status = statusRes.rows[0]?.status as string | undefined;
      if (status === "cancelling") {
        await pool.query(
          `UPDATE jobs
           SET status = 'cancelled', finished_at = now(),
               status_message = 'Cancelled', progress_pct = $2, updated_at = now()
           WHERE id = $1`,
          [jobId, progressForStep(step.key, params)],
        );
        await pool.query(
          `UPDATE job_steps
           SET status = 'cancelled', finished_at = now(), message = 'Cancelled'
           WHERE job_id = $1 AND status IN ('pending', 'running')`,
          [jobId],
        );
        await pool.query(
          `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'warn', $2)`,
          [jobId, "Stub worker cancelled"],
        );
        return;
      }

      await pool.query(
        `UPDATE job_steps
         SET status = 'running', started_at = now(), message = $3
         WHERE job_id = $1 AND step_key = $2`,
        [jobId, step.key, `Running ${step.label}`],
      );
      await pool.query(
        `UPDATE jobs
         SET current_step = $2, progress_pct = $3,
             status_message = $4, updated_at = now()
         WHERE id = $1`,
        [
          jobId,
          step.key,
          progressForStep(step.key, params),
          `Running: ${step.label}`,
        ],
      );
      await pool.query(
        `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'info', $2)`,
        [jobId, `[stub] ${step.label}`],
      );

      await new Promise((r) => setTimeout(r, 800));

      const done =
        step.key === "done"
          ? "succeeded"
          : step.key === "kaggle_upload" && !params.includeKaggle
            ? "skipped"
            : "succeeded";

      await pool.query(
        `UPDATE job_steps
         SET status = $3, finished_at = now(), message = $4
         WHERE job_id = $1 AND step_key = $2`,
        [jobId, step.key, done, `${step.label} complete`],
      );
    }

    await pool.query(
      `UPDATE jobs
       SET status = 'succeeded', finished_at = now(), progress_pct = 100,
           current_step = 'done', status_message = 'Stub import complete',
           updated_at = now()
       WHERE id = $1`,
      [jobId],
    );
    await pool.query(
      `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'info', $2)`,
      [jobId, "Stub worker finished successfully"],
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    await pool.query(
      `UPDATE jobs
       SET status = 'failed', finished_at = now(), error = $2,
           status_message = 'Stub worker failed', updated_at = now()
       WHERE id = $1`,
      [jobId, message],
    );
    await pool.query(
      `INSERT INTO job_logs (job_id, level, message) VALUES ($1, 'error', $2)`,
      [jobId, `Stub worker error: ${message}`],
    );
  }
}

/**
 * Local mode: spawn the Python worker in a child process (requires Python deps).
 */
export async function triggerLocalWorker(jobId: string): Promise<void> {
  const { spawn } = await import("child_process");
  const path = await import("path");

  const entry = path.join(process.cwd(), "worker", "entrypoint.py");
  // Prefer WORKER_PYTHON. Avoid embedding ".venv" as a literal path segment —
  // Turbopack tries to resolve it and panics on the venv symlink.
  const pythonBin = process.env.WORKER_PYTHON || "python3";

  await appendJobLog(jobId, `Spawning local worker: ${pythonBin} ${entry}`);
  await setCloudRunExecution(jobId, `local://${process.pid}`);

  const child = spawn(pythonBin, [entry], {
    env: { ...process.env, JOB_ID: jobId },
    detached: true,
    stdio: "ignore",
  });
  child.unref();
}

export async function triggerWorker(jobId: string): Promise<void> {
  const mode = getWorkerMode();
  if (mode === "cloud_run") {
    await triggerCloudRunJob(jobId);
    return;
  }
  if (mode === "local") {
    await triggerLocalWorker(jobId);
    return;
  }
  await triggerStubWorker(jobId);
}
