export const PIPELINE_STEPS = [
  { key: "queued", label: "Queued", order: 0 },
  { key: "load_fastf1", label: "Load FastF1", order: 1 },
  { key: "resample_telemetry", label: "Resample telemetry", order: 2 },
  { key: "upload_kaggle_export", label: "Upload Kaggle export", order: 3 },
  { key: "upload_sessions_laps", label: "Upload sessions & laps", order: 4 },
  { key: "upload_telemetry", label: "Upload telemetry", order: 5 },
  { key: "verify", label: "Verify upload", order: 6 },
  { key: "quality_checks", label: "Quality checks", order: 7 },
  { key: "laps_unified", label: "Update laps_unified", order: 8 },
  { key: "kaggle_upload", label: "Kaggle upload", order: 9 },
  { key: "done", label: "Done", order: 10 },
] as const;

export type StepKey = (typeof PIPELINE_STEPS)[number]["key"];

export const SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"] as const;
export type SessionType = (typeof SESSION_TYPES)[number];

export type JobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "cancelled"
  | "succeeded"
  | "failed";

export type JobStepStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "skipped"
  | "cancelled";

export type JobParams = {
  years: number[];
  race: string;
  sessions: SessionType[];
  /** Optional map of session code → schedule label (e.g. Q → Qualifying). */
  sessionLabels?: Record<string, string>;
  noSkip: boolean;
  skipQuality: boolean;
  skipUnified: boolean;
  includeKaggle: boolean;
};

const WAREHOUSE_STEPS = new Set([
  "upload_sessions_laps",
  "upload_telemetry",
  "verify",
  "laps_unified",
]);

const KAGGLE_ONLY_STEPS = new Set(["upload_kaggle_export", "kaggle_upload"]);

export function stepsForParams(params: JobParams) {
  return PIPELINE_STEPS.filter((step) => {
    if (params.includeKaggle) {
      if (WAREHOUSE_STEPS.has(step.key)) return false;
    } else if (KAGGLE_ONLY_STEPS.has(step.key)) {
      return false;
    }
    if (step.key === "quality_checks" && params.skipQuality) return false;
    if (step.key === "laps_unified" && params.skipUnified) return false;
    return true;
  });
}

export function progressForStep(stepKey: string, params: JobParams): number {
  const steps = stepsForParams(params);
  const idx = steps.findIndex((s) => s.key === stepKey);
  if (idx < 0) return 0;
  if (stepKey === "done") return 100;
  return Math.round((idx / Math.max(steps.length - 1, 1)) * 1000) / 10;
}
