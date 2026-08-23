import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { BigQuery } from "@google-cloud/bigquery";
import type { CatalogEvent, ImportCatalog } from "./session-map";
import { SESSION_TYPES, type JobParams, type SessionType } from "./steps";

const execFileAsync = promisify(execFile);

function getBigQuery(): BigQuery {
  const projectId =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const keyJson = process.env.GOOGLE_SERVICE_ACCOUNT_KEY;
  if (keyJson) {
    return new BigQuery({ projectId, credentials: JSON.parse(keyJson) });
  }
  const keyFile = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (keyFile) {
    return new BigQuery({ projectId, keyFilename: keyFile });
  }
  return new BigQuery({ projectId });
}

export async function loadFastf1Schedule(
  year: number,
  race?: string,
): Promise<ImportCatalog> {
  const pythonBin = process.env.WORKER_PYTHON || "python3";
  const script = path.join(
    process.cwd(),
    "worker",
    "pipeline",
    "fastf1_schedule.py",
  );
  const args = [script, "--year", String(year)];
  if (race?.trim()) args.push("--race", race.trim());

  let stdout: string;
  let stderr: string;
  try {
    const result = await execFileAsync(pythonBin, args, {
      timeout: 60_000,
      maxBuffer: 8 * 1024 * 1024,
      env: process.env,
    });
    stdout = result.stdout;
    stderr = result.stderr;
  } catch (err) {
    const e = err as {
      stderr?: string;
      stdout?: string;
      message?: string;
      code?: string;
    };
    const detail = (e.stderr || e.stdout || e.message || String(err)).trim();
    if (e.code === "ENOENT") {
      throw new Error(
        `Python not found (${pythonBin}). Install Python 3 and FastF1 worker deps, or set WORKER_PYTHON.`,
      );
    }
    throw new Error(
      detail ||
        "Failed to load FastF1 schedule. Install worker deps: pip install -r worker/requirements.txt",
    );
  }

  // FastF1 may print cache warnings to stderr; parse last JSON object from stdout
  const text = stdout.trim();
  if (!text) {
    throw new Error(
      stderr.trim() ||
        "FastF1 schedule script returned empty output. Is fastf1 installed?",
    );
  }
  const jsonLine = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .reverse()
    .find((l) => l.startsWith("{"));
  if (!jsonLine) {
    throw new Error(`Unexpected schedule output: ${text.slice(0, 200)}`);
  }

  const parsed = JSON.parse(jsonLine) as ImportCatalog & { error?: string };
  if (parsed.error) throw new Error(parsed.error);
  if (!parsed.events) throw new Error("Schedule response missing events");
  return { year: parsed.year, events: parsed.events };
}

export async function fetchImportedSessionKeys(
  year: number,
): Promise<Set<string>> {
  const project =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const dataset = process.env.BQ_DATASET || "f1_data_library_DS";
  const bq = getBigQuery();
  const sql = `
    SELECT DISTINCT
      CAST(season AS INT64) AS season,
      event_name,
      session_type
    FROM \`${project}.${dataset}.telemetry\`
    WHERE season = @year
  `;
  try {
    const [rows] = await bq.query({
      query: sql,
      params: { year },
      types: { year: "INT64" },
    });
    const keys = new Set<string>();
    for (const row of rows as Array<{
      season: number;
      event_name: string;
      session_type: string;
    }>) {
      keys.add(
        `${row.season}|${row.event_name}|${row.session_type}`.toLowerCase(),
      );
    }
    return keys;
  } catch (err) {
    // Catalog still useful without badges
    console.warn(
      "[import-catalog] BQ presence query failed:",
      err instanceof Error ? err.message : err,
    );
    return new Set();
  }
}

export async function loadImportCatalog(
  year: number,
  race?: string,
): Promise<ImportCatalog> {
  const schedule = await loadFastf1Schedule(year, race);
  const imported = await fetchImportedSessionKeys(year);

  const events: CatalogEvent[] = schedule.events.map((ev) => ({
    ...ev,
    sessions: ev.sessions.map((s) => ({
      ...s,
      inBigQuery: imported.has(
        `${year}|${ev.eventName}|${s.code}`.toLowerCase(),
      ),
    })),
  }));

  return { year, events };
}

function skipFastf1Catalog(): boolean {
  const explicit = (process.env.SKIP_FASTF1_CATALOG || "").toLowerCase();
  if (explicit === "1" || explicit === "true" || explicit === "yes") {
    return true;
  }
  // Vercel Node serverless has no python3 / FastF1. Session codes are still
  // checked by parseJobParams against SESSION_TYPES.
  return process.env.VERCEL === "1";
}

function isPythonMissing(err: unknown): boolean {
  const e = err as { code?: string; message?: string };
  if (e.code === "ENOENT") return true;
  const msg = (e.message || String(err)).toLowerCase();
  return msg.includes("python not found") || msg.includes("enoent");
}

export async function validateJobParamsAgainstCatalog(
  params: JobParams,
): Promise<void> {
  if (skipFastf1Catalog()) {
    console.warn(
      "[import-catalog] Skipping FastF1 schedule check (VERCEL or SKIP_FASTF1_CATALOG). Session types are still validated.",
    );
    return;
  }

  try {
    for (const year of params.years) {
      const catalog = await loadImportCatalog(year, params.race);
      const event = catalog.events.find(
        (e) => e.eventName.toLowerCase() === params.race.toLowerCase(),
      );
      if (!event) {
        throw new Error(
          `Race "${params.race}" not found in ${year} FastF1 schedule`,
        );
      }
      const allowed = new Set(event.sessions.map((s) => s.code));
      for (const code of params.sessions) {
        if (!allowed.has(code)) {
          const format = event.eventFormat || "unknown format";
          throw new Error(
            `${code} is not a session for ${params.race} ${year} (${format})`,
          );
        }
      }
    }
  } catch (err) {
    if (isPythonMissing(err)) {
      console.warn(
        "[import-catalog] FastF1 schedule unavailable; skipping catalog check:",
        err instanceof Error ? err.message : err,
      );
      return;
    }
    throw err;
  }
}

export function assertSessionType(code: string): code is SessionType {
  return (SESSION_TYPES as readonly string[]).includes(code);
}
