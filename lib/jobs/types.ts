import type { JobParams, JobStatus, JobStepStatus } from "./steps";

export type { JobParams, JobStatus, JobStepStatus };

export type JobRow = {
  id: string;
  status: JobStatus;
  params: JobParams;
  progress_pct: number;
  current_step: string | null;
  status_message: string | null;
  error: string | null;
  cloud_run_execution_name: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
};

export type JobStepRow = {
  id: string;
  job_id: string;
  step_key: string;
  step_order: number;
  status: JobStepStatus;
  message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type JobLogRow = {
  id: number;
  job_id: string;
  ts: string;
  level: string;
  message: string;
};

export type JobDetail = JobRow & {
  steps: JobStepRow[];
  logs: JobLogRow[];
};
