export const PIPELINE_STEPS = [
  { key: "queued", label: "Queued", order: 0 },
  { key: "load_fastf1", label: "Load FastF1", order: 1 },
  { key: "resample_telemetry", label: "Resample telemetry", order: 2 },
  { key: "upload_sessions_laps", label: "Upload sessions & laps", order: 3 },
  { key: "upload_telemetry", label: "Upload telemetry", order: 4 },
  { key: "verify", label: "Verify upload", order: 5 },
  { key: "quality_checks", label: "Quality checks", order: 6 },
  { key: "laps_unified", label: "Update laps_unified", order: 7 },
  { key: "kaggle_upload", label: "Kaggle upload", order: 8 },
  { key: "done", label: "Done", order: 9 },
] as const;

export type StepKey = (typeof PIPELINE_STEPS)[number]["key"];

export const SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "SQ", "R"] as const;
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
  noSkip: boolean;
  skipQuality: boolean;
  skipUnified: boolean;
  includeKaggle: boolean;
};

export function stepsForParams(params: JobParams) {
  return PIPELINE_STEPS.filter((step) => {
    if (step.key === "quality_checks" && params.skipQuality) return false;
    if (step.key === "laps_unified" && params.skipUnified) return false;
    if (step.key === "kaggle_upload" && !params.includeKaggle) return false;
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
