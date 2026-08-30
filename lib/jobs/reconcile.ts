import { getCloudRunExecution } from "./cloud-run";
import { forceFailJob } from "./queries";
import type { JobRow } from "./types";

const STALE_MS = 15 * 60 * 1000;

function isActive(status: JobRow["status"]): boolean {
  return status === "running" || status === "cancelling" || status === "queued";
}

async function failIfStale(job: JobRow): Promise<boolean> {
  const updated = Date.parse(job.updated_at);
  if (!Number.isFinite(updated)) return false;
  const age = Date.now() - updated;
  if (age < STALE_MS) return false;
  const mins = Math.max(1, Math.round(age / 60_000));
  const result = await forceFailJob(
    job.id,
    `Watchdog: no worker heartbeat for ${mins} min (Cloud Run likely SIGKILL or hung)`,
  );
  return Boolean(result);
}

/** If Cloud Run is dead (or the worker went silent), mark the Postgres job failed. */
export async function reconcileJobExecution(job: JobRow): Promise<boolean> {
  if (!isActive(job.status)) return false;

  const name = job.cloud_run_execution_name;
  if (!name || name.startsWith("stub://") || name.startsWith("local://")) {
    return failIfStale(job);
  }

  let exec: Awaited<ReturnType<typeof getCloudRunExecution>> = null;
  try {
    exec = await getCloudRunExecution(name);
  } catch (err) {
    console.warn(
      "[reconcile] Cloud Run get failed:",
      err instanceof Error ? err.message : err,
    );
    return failIfStale(job);
  }

  const status = (exec?.completionStatus || "").toUpperCase();
  if (status.includes("FAILED")) {
    const result = await forceFailJob(
      job.id,
      `Cloud Run execution failed: ${name}`,
    );
    return Boolean(result);
  }
  if (status.includes("CANCELLED")) {
    const result = await forceFailJob(
      job.id,
      `Cloud Run execution cancelled: ${name}`,
    );
    return Boolean(result);
  }
  if (status.includes("SUCCEEDED") && job.status !== "succeeded") {
    const result = await forceFailJob(
      job.id,
      `Cloud Run execution finished but job still ${job.status} — worker died before finalize`,
    );
    return Boolean(result);
  }

  return failIfStale(job);
}

export async function reconcileActiveJobs(jobs: JobRow[]): Promise<number> {
  let changed = 0;
  for (const job of jobs) {
    if (!isActive(job.status)) continue;
    if (await reconcileJobExecution(job)) changed += 1;
  }
  return changed;
}
