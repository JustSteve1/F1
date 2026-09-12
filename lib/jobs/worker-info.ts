import { getWorkerMode, type WorkerMode } from "./cloud-run";

export type WorkerInfo = {
  mode: WorkerMode;
  ingestSource: string;
  ingestOk: boolean;
  stub: boolean;
  jobName: string;
  region: string;
};

export function getWorkerInfo(): WorkerInfo {
  const mode = getWorkerMode();
  const raw = (process.env.INGEST_SOURCE || "fastf1").trim().toLowerCase() || "fastf1";
  const ingestOk = raw === "fastf1";
  return {
    mode,
    ingestSource: raw,
    ingestOk,
    stub: mode === "stub",
    jobName: process.env.CLOUD_RUN_JOB_NAME || "f1-telemetry-import",
    region: process.env.CLOUD_RUN_REGION || "europe-west1",
  };
}
