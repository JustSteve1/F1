import type { JobStatus } from "./steps";

export type ReconcileAction = "failed" | "cancelled" | "check-stale";

/**
 * Map a Cloud Run execution completionStatus onto the Postgres job.
 * Admin Cancel stops the execution, so CANCELLED must become cancelled
 * (not failed) or the UI looks like a crash.
 */
export function mapCloudRunCompletion(
  jobStatus: JobStatus,
  completionStatus: string | null,
): ReconcileAction {
  const status = (completionStatus || "").toUpperCase();
  if (status.includes("FAILED")) return "failed";
  if (status.includes("CANCELLED")) return "cancelled";
  if (status.includes("SUCCEEDED") && jobStatus !== "succeeded") {
    return "failed";
  }
  return "check-stale";
}
