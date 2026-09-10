import { PIPELINE_STEPS, type StepKey } from "./steps";

export type SampleTable = {
  columns: string[];
  rows: (string | number | boolean | null)[][];
};

export type PipelineGuideStep = {
  key: StepKey;
  label: string;
  notebookCell: string | null;
  short: string;
  detail: string;
  writes: string[];
  inputs: string[];
  outputs: string[];
  sample: SampleTable | null;
};

/** Prelude shown on the explainer (notebook Cells 0–1), not a job step. */
export const PIPELINE_PRELUDE = {
  notebookCell: "Cells 0–1",
  title: "Select & configure",
  short: "Choose years, race, sessions, and skip-existing behavior.",
  detail:
    "The Colab notebook uses widgets to pick years (2018+), an event name, session types (FP1…R), and whether to skip data already in BigQuery. The jobs admin form is the same gate: params become JobParams before the worker runs.",
  demoConfig: {
    years: [2025],
    race: "Australian Grand Prix",
    sessions: ["R"] as const,
    skipExisting: true,
  },
};

export const PIPELINE_GUIDE: Record<StepKey, PipelineGuideStep> = {
  queued: {
    key: "queued",
    label: "Queued",
    notebookCell: null,
    short: "Job accepted; waiting for the worker.",
    detail:
      "The control plane writes the job and step rows to Postgres, then triggers Cloud Run (or the local stub). No FastF1 or BigQuery work yet.",
    writes: [],
    inputs: ["JobParams (years, race, sessions, flags)"],
    outputs: ["Job row in Postgres", "Pending step timeline"],
    sample: {
      columns: ["field", "value"],
      rows: [
        ["status", "queued"],
        ["race", "Australian Grand Prix"],
        ["years", "2025"],
        ["sessions", "R"],
      ],
    },
  },
  load_fastf1: {
    key: "load_fastf1",
    label: "Load FastF1",
    notebookCell: "Cell 2",
    short: "Download session telemetry and laps from FastF1.",
    detail:
      "For each year × session, call fastf1.get_session and load telemetry + laps. Sessions already present in BigQuery are skipped when skip-existing is on. Invalid or empty events are dropped.",
    writes: [],
    inputs: ["Year", "Event name", "Session type"],
    outputs: ["In-memory FastF1 Session objects"],
    sample: {
      columns: ["year", "session", "event", "drivers", "laps"],
      rows: [[2025, "R", "Australian Grand Prix", 20, 1142]],
    },
  },
  resample_telemetry: {
    key: "resample_telemetry",
    label: "Resample telemetry",
    notebookCell: "Cell 3",
    short: "Nearest-neighbor resample to 10 Hz (0.1 s), then checkpoint to GCS.",
    detail:
      "For each lap, pick the closest FastF1 sample to every 0.1 s tick. Captures speed, throttle, brake, gear, RPM, DRS, XYZ, deceleration, and distance. Dedupes on season/session/driver/lap/lap_time_sec. Writes Parquet to gs://f1-data-library-fastf1-cache/staging/{job_id}/ so a killed upload can skip this step on the same JOB_ID. Staging is deleted after a successful run. Kaggle jobs pack these 10 Hz points into for_kaggle_export.telemetry; warehouse jobs write the telemetry table.",
    writes: [],
    inputs: ["Per-lap FastF1 telemetry"],
    outputs: ["telemetry_df (10 Hz points)", "Thin laps_df metadata"],
    sample: {
      columns: [
        "driver",
        "lap",
        "t_sec",
        "speed",
        "throttle",
        "brake",
        "gear",
        "x",
        "y",
      ],
      rows: [
        ["1", 12, 0.0, 298.1, 100, false, 8, 412.3, -180.2],
        ["1", 12, 0.1, 301.4, 100, false, 8, 428.7, -175.1],
        ["1", 12, 0.2, 304.0, 98, false, 8, 445.0, -169.8],
        ["1", 12, 0.3, 288.2, 20, true, 7, 460.1, -164.0],
        ["1", 12, 0.4, 265.5, 0, true, 6, 473.8, -158.6],
      ],
    },
  },
  upload_kaggle_export: {
    key: "upload_kaggle_export",
    label: "Upload Kaggle export",
    notebookCell: null,
    short: "Write the 13-column for_kaggle_export table at 10 Hz.",
    detail:
      "Kaggle-only path. Builds one row per lap matching All Laps CSV columns (season, event, circuit, session, driver, numbers, lap_time, duration, compound, tyre_age, stint, telemetry JSON). Telemetry is the 10 Hz resample — not the old 2 Hz downsample. Deletes existing rows for this season/event/session, then bulk-loads. Does not write sessions, laps, or telemetry warehouse tables. telemetry is STRING so Parquet loads cannot hit BigQuery JSON rejection.",
    writes: ["for_kaggle_export"],
    inputs: ["Loaded sessions", "telemetry_df (10 Hz)"],
    outputs: ["for_kaggle_export rows"],
    sample: {
      columns: [
        "season",
        "event_name",
        "session_type",
        "driver",
        "lap_number",
        "lap_time",
      ],
      rows: [[2026, "Italian Grand Prix", "R", "VER", 12, "1:21.234"]],
    },
  },
  upload_sessions_laps: {
    key: "upload_sessions_laps",
    label: "Upload sessions & laps",
    notebookCell: "Cell 4",
    short: "Insert session rows; bulk-load laps.",
    detail:
      "session_key is derived from MD5(year-race-session) truncated to 8 hex digits. Existing laps and telemetry for those session_keys are deleted first (replace, not append). Sessions are skipped if the session_key already exists. Laps are bulk-loaded via a BigQuery load job.",
    writes: ["sessions", "laps"],
    inputs: ["Loaded sessions", "laps_df"],
    outputs: ["sessions rows", "laps rows", "session_key"],
    sample: {
      columns: ["session_key", "season", "event_name", "session_type", "laps"],
      rows: [[2847192031, 2025, "Australian Grand Prix", "R", 1142]],
    },
  },
  upload_telemetry: {
    key: "upload_telemetry",
    label: "Upload telemetry",
    notebookCell: "Cell 5",
    short: "Bulk-load 10 Hz points into telemetry.",
    detail:
      "Adds session_key/meeting_key and import timestamps, deletes any existing telemetry for those session_keys, then appends via a BigQuery load job (load_table_from_dataframe). Reads the in-memory frame or, if missing, the GCS resample checkpoint. On type failure, writes Parquet to gs://f1-data-library-fastf1-cache/staging/{job_id}/ and loads from URI. Job id and row count are logged to Postgres.",
    writes: ["telemetry"],
    inputs: ["Resampled telemetry_df"],
    outputs: ["telemetry rows in BigQuery"],
    sample: {
      columns: [
        "session_key",
        "driver_number",
        "lap_number",
        "lap_time_sec",
        "speed",
        "interval_sec",
      ],
      rows: [
        [2847192031, "1", 12, 0.0, 298.1, 0.1],
        [2847192031, "1", 12, 0.1, 301.4, 0.1],
        [2847192031, "1", 12, 0.2, 304.0, 0.1],
      ],
    },
  },
  verify: {
    key: "verify",
    label: "Verify upload",
    notebookCell: "Cell 6",
    short: "Sanity-check counts, nulls, and XYZ coverage.",
    detail:
      "Queries telemetry/sessions/laps for the event: point counts, drivers, unique laps, null rates, duplicate keys. Notebook also plots racing lines and a sample lap; the worker logs verification summaries.",
    writes: [],
    inputs: ["telemetry", "sessions", "laps"],
    outputs: ["Verification summary", "Quality signals"],
    sample: {
      columns: [
        "session_type",
        "total_points",
        "drivers",
        "unique_laps",
        "xyz_pct",
      ],
      rows: [["R", 842_150, 20, 1142, 98.4]],
    },
  },
  quality_checks: {
    key: "quality_checks",
    label: "Quality checks",
    notebookCell: "Cells 7–8",
    short: "Flag data-quality exceptions.",
    detail:
      "Warehouse jobs validate missing sectors, invalid lap times, telemetry gaps, and sequence holes on laps/telemetry. Kaggle jobs only inspect for_kaggle_export: missing driver or lap_number, null lap_duration, empty telemetry JSON. Exceptions still land in data_quality_exceptions.",
    writes: ["data_quality_exceptions"],
    inputs: ["for_kaggle_export or laps/telemetry"],
    outputs: ["Exception report"],
    sample: {
      columns: [
        "severity",
        "category",
        "driver_number",
        "lap_number",
        "issue_type",
      ],
      rows: [
        ["warning", "missing_data", "44", 3, "missing_sectors"],
        ["critical", "missing_telemetry", "11", 18, "no_telemetry"],
        ["warning", "missing_laps", "16", 0, "gap 14→16"],
      ],
    },
  },
  laps_unified: {
    key: "laps_unified",
    label: "Update laps_unified",
    notebookCell: "Cell 9",
    short: "Derive analytics-ready laps from telemetry + laps.",
    detail:
      "Joins lap timing (ms), tyre/stint context, speed traps, and telemetry coverage flags. Deletes existing rows for the session_id then appends. Marks laps validated / suspect / legacy by point count.",
    writes: ["laps_unified"],
    inputs: ["laps", "telemetry", "circuit_metadata"],
    outputs: ["laps_unified rows"],
    sample: {
      columns: [
        "session_id",
        "driver_code",
        "lap_number",
        "lap_time_ms",
        "compound",
        "data_quality",
      ],
      rows: [
        [2847192031, "VER", 12, 81234, "MEDIUM", "validated"],
        [2847192031, "NOR", 12, 81302, "MEDIUM", "validated"],
        [2847192031, "HAM", 3, null, "SOFT", "suspect"],
      ],
    },
  },
  kaggle_upload: {
    key: "kaggle_upload",
    label: "Kaggle upload",
    notebookCell: null,
    short: "Publish for_kaggle_export as All Laps CSV.",
    detail:
      "Downloads the current Kaggle dataset, replaces any lap keys that exist in for_kaggle_export (so noSkip re-imports refresh 10 Hz blobs), keeps historical CSV rows that were never imported via this table, and uploads a new dataset version. Does not join warehouse laps or downsample telemetry.",
    writes: [],
    inputs: ["for_kaggle_export", "Existing Kaggle CSV"],
    outputs: ["Kaggle dataset revision"],
    sample: {
      columns: ["artifact", "status"],
      rows: [["All Laps - 10 September 2026.csv", "uploaded"]],
    },
  },
  done: {
    key: "done",
    label: "Done",
    notebookCell: null,
    short: "Pipeline finished successfully.",
    detail:
      "All selected steps completed. Telemetry is queryable in BigQuery and ready for pitwall / ML analysis.",
    writes: [],
    inputs: ["Prior step outputs"],
    outputs: ["Succeeded job status"],
    sample: {
      columns: ["metric", "value"],
      rows: [
        ["status", "succeeded"],
        ["progress_pct", 100],
      ],
    },
  },
};

/** Guide steps in pipeline order (excludes nothing — full rail for explainer). */
export const PIPELINE_GUIDE_STEPS = PIPELINE_STEPS.map(
  (s) => PIPELINE_GUIDE[s.key],
);

/** Visible rail for guide mode: skip pure bookends if desired; keep all for clarity. */
export const PIPELINE_GUIDE_RAIL = PIPELINE_GUIDE_STEPS.filter(
  (s) => s.key !== "queued" && s.key !== "done",
);

export function guideForKey(key: string): PipelineGuideStep | undefined {
  return PIPELINE_GUIDE[key as StepKey];
}
