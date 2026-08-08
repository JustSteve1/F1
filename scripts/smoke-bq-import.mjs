#!/usr/bin/env node
/**
 * Smoke test: create a cloud_run telemetry import job and verify BigQuery rows.
 *
 * Usage:
 *   pnpm smoke:bq-import
 *   SMOKE_BASE_URL=http://localhost:3001 pnpm smoke:bq-import
 *
 * Exit 0 = PASS, 1 = FAIL
 */

import { GoogleAuth } from "google-auth-library";
import { BigQuery } from "@google-cloud/bigquery";

const BASE_URL = (process.env.SMOKE_BASE_URL || "http://localhost:3000").replace(
  /\/$/,
  "",
);
const POLL_MS = Number(process.env.SMOKE_POLL_MS || 5000);
const TIMEOUT_MS = Number(process.env.SMOKE_TIMEOUT_MS || 60 * 60 * 1000);
const FETCH_TIMEOUT_MS = Number(process.env.SMOKE_FETCH_TIMEOUT_MS || 120_000);

async function fetchJson(url, init = {}) {
  const res = await fetch(url, {
    ...init,
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  });
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { res, data };
}

const JOB_PARAMS = {
  years: [2026],
  race: "Monaco Grand Prix",
  sessions: ["R"],
  noSkip: false,
  skipQuality: false,
  skipUnified: false,
  includeKaggle: false,
};

function fail(msg, extra) {
  console.error("\n❌ FAIL:", msg);
  if (extra) console.error(extra);
  process.exit(1);
}

function ok(msg) {
  console.log("✓", msg);
}

function getGoogleAuth() {
  const scopes = ["https://www.googleapis.com/auth/cloud-platform"];
  const keyJson = process.env.GOOGLE_SERVICE_ACCOUNT_KEY?.trim();
  if (keyJson) {
    return new GoogleAuth({
      credentials: JSON.parse(keyJson),
      scopes,
    });
  }
  const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL?.trim();
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  if (email && privateKey) {
    return new GoogleAuth({
      credentials: { client_email: email, private_key: privateKey },
      scopes,
    });
  }
  return new GoogleAuth({ scopes });
}

function getBigQuery() {
  const projectId =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const keyJson = process.env.GOOGLE_SERVICE_ACCOUNT_KEY?.trim();
  if (keyJson) {
    return new BigQuery({ projectId, credentials: JSON.parse(keyJson) });
  }
  const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL?.trim();
  const privateKey = process.env.GOOGLE_PRIVATE_KEY?.replace(/\\n/g, "\n");
  if (email && privateKey) {
    return new BigQuery({
      projectId,
      credentials: { client_email: email, private_key: privateKey },
    });
  }
  return new BigQuery({ projectId });
}

async function preflightEnv() {
  console.log("\n── Preflight: env ──");
  const mode = (process.env.JOB_WORKER_MODE || "stub").toLowerCase();
  if (mode !== "cloud_run") {
    fail(
      `JOB_WORKER_MODE must be cloud_run (got "${mode}"). Refusing stub/local.`,
    );
  }
  ok(`JOB_WORKER_MODE=${mode}`);

  for (const key of ["DATABASE_URL", "GCP_PROJECT_ID"]) {
    if (!process.env[key]?.trim()) fail(`Missing required env: ${key}`);
    ok(`${key} is set`);
  }

  const bqProject = process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID;
  const bqDataset = process.env.BQ_DATASET || "f1_data_library_DS";
  ok(`BigQuery target: ${bqProject}.${bqDataset}.telemetry`);

  try {
    const { res, data } = await fetchJson(`${BASE_URL}/api/admin/jobs`, {
      cache: "no-store",
    });
    if (!res.ok) {
      fail(
        `Admin API not healthy at ${BASE_URL} (${res.status})`,
        data?.error || JSON.stringify(data)?.slice(0, 400),
      );
    }
    ok(`Admin API reachable at ${BASE_URL}`);
  } catch (err) {
    fail(
      `Cannot reach ${BASE_URL}. Start the Next.js server (pnpm dev) and ensure Cloud SQL is reachable.`,
      err instanceof Error ? err.message : String(err),
    );
  }
}

async function preflightDryRun() {
  console.log("\n── Preflight: Cloud Run WORKER_DRY_RUN ──");
  const project = process.env.GCP_PROJECT_ID;
  const region = process.env.CLOUD_RUN_REGION || "europe-west1";
  const jobName = process.env.CLOUD_RUN_JOB_NAME || "f1-telemetry-import";
  const name = `projects/${project}/locations/${region}/jobs/${jobName}`;
  const url = `https://run.googleapis.com/v2/${name}`;

  const auth = getGoogleAuth();
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  if (!token.token) fail("Failed to obtain GCP access token");

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token.token}` },
  });
  if (!res.ok) {
    const text = await res.text();
    fail(`Cloud Run job describe failed (${res.status})`, text.slice(0, 500));
  }

  const data = await res.json();
  const envVars =
    data?.template?.template?.containers?.[0]?.env ||
    data?.template?.containers?.[0]?.env ||
    [];

  const dry = envVars.find((e) => e.name === "WORKER_DRY_RUN");
  const dryVal = (dry?.value || "").toLowerCase();
  if (dryVal === "1" || dryVal === "true" || dryVal === "yes") {
    fail(
      `Cloud Run job ${jobName} still has WORKER_DRY_RUN=${dry.value}. ` +
        "Clear it before this smoke test can verify BigQuery writes:\n" +
        `  gcloud run jobs update ${jobName} --project=${project} --region=${region} --remove-env-vars=WORKER_DRY_RUN`,
    );
  }
  ok(
    dry
      ? `WORKER_DRY_RUN present but disabled (${dry.value})`
      : "WORKER_DRY_RUN not set (live writes enabled)",
  );
  ok(`Cloud Run job: ${name}`);
}

async function createJob() {
  console.log("\n── Create import job ──");
  console.log("Params:", JSON.stringify(JOB_PARAMS));

  const { res, data } = await fetchJson(`${BASE_URL}/api/admin/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(JOB_PARAMS),
  });
  if (!res.ok) {
    fail(`Create job failed (${res.status})`, data?.error || JSON.stringify(data));
  }
  if (data.warning) {
    fail("Job created but worker trigger failed", data.warning);
  }

  const job = data.job;
  if (!job?.id) fail("Create response missing job.id", JSON.stringify(data));
  ok(`Job created: ${job.id}`);
  return job;
}

async function pollJob(jobId) {
  console.log("\n── Poll job until terminal ──");
  const deadline = Date.now() + TIMEOUT_MS;
  let lastStatus = "";

  while (Date.now() < deadline) {
    const { res, data } = await fetchJson(`${BASE_URL}/api/admin/jobs/${jobId}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      fail(`Poll failed (${res.status})`, data?.error || JSON.stringify(data));
    }

    const job = data.job;
    const status = job.status;
    if (status !== lastStatus) {
      console.log(
        `  [${new Date().toISOString()}] status=${status}` +
          (job.current_step ? ` step=${job.current_step}` : "") +
          (job.progress_pct != null ? ` ${Math.round(job.progress_pct)}%` : "") +
          (job.status_message ? ` — ${job.status_message}` : ""),
      );
      lastStatus = status;
    }

    if (status === "succeeded" || status === "failed" || status === "cancelled") {
      return job;
    }

    await new Promise((r) => setTimeout(r, POLL_MS));
  }

  fail(`Timed out after ${TIMEOUT_MS / 1000}s waiting for job ${jobId}`);
}

async function verifyBigQuery(job) {
  console.log("\n── Verify BigQuery telemetry ──");
  const project =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const dataset = process.env.BQ_DATASET || "f1_data_library_DS";
  const table = `\`${project}.${dataset}.telemetry\``;

  const bq = getBigQuery();
  const [rows] = await bq.query({
    query: `
      SELECT
        COUNT(*) AS n,
        MIN(imported_at) AS first_import,
        MAX(imported_at) AS last_import
      FROM ${table}
      WHERE season = @season
        AND event_name = @event_name
        AND session_type = @session_type
    `,
    params: {
      season: JOB_PARAMS.years[0],
      event_name: JOB_PARAMS.race,
      session_type: JOB_PARAMS.sessions[0],
    },
  });

  const row = rows[0] || {};
  const n = Number(row.n || 0);
  const firstImport = row.first_import?.value || row.first_import || null;
  const lastImport = row.last_import?.value || row.last_import || null;

  console.log(`  rows:         ${n.toLocaleString()}`);
  console.log(`  first_import: ${firstImport ?? "—"}`);
  console.log(`  last_import:  ${lastImport ?? "—"}`);

  const startedAt = job.started_at || job.created_at;
  let freshness = "unknown";
  if (lastImport && startedAt) {
    freshness =
      new Date(lastImport).getTime() >= new Date(startedAt).getTime()
        ? "fresh import (last_import >= job.started_at)"
        : "data already present (skip-existing)";
  }
  console.log(`  freshness:    ${freshness}`);

  return { n, firstImport, lastImport, freshness };
}

function printVerdict(job, bq) {
  console.log("\n══════════════════════════════════════");
  console.log("SMOKE TEST VERDICT");
  console.log("══════════════════════════════════════");
  console.log(`job_id:                  ${job.id}`);
  console.log(`status:                  ${job.status}`);
  console.log(`cloud_run_execution:     ${job.cloud_run_execution_name || "—"}`);
  console.log(`error:                   ${job.error || "—"}`);
  console.log(`bq_telemetry_rows:       ${bq.n}`);
  console.log(`bq_freshness:            ${bq.freshness}`);

  const hasExecution = Boolean(job.cloud_run_execution_name);
  const succeeded = job.status === "succeeded";
  const hasRows = bq.n > 0;

  if (succeeded && hasExecution && hasRows) {
    console.log("\n✅ PASS — job succeeded, Cloud Run triggered, BigQuery has telemetry rows.");
    process.exit(0);
  }

  const reasons = [];
  if (!succeeded) reasons.push(`job status is ${job.status}`);
  if (!hasExecution) reasons.push("missing cloud_run_execution_name");
  if (!hasRows) reasons.push("no telemetry rows for 2026 Monaco Grand Prix R");

  if (job.logs?.length) {
    console.log("\n── Last logs ──");
    for (const log of job.logs.slice(-20)) {
      console.log(`  [${log.level}] ${log.message}`);
    }
  }

  fail(reasons.join("; "));
}

async function main() {
  console.log("BigQuery import smoke test");
  console.log(`Base URL: ${BASE_URL}`);

  await preflightEnv();
  await preflightDryRun();
  const created = await createJob();
  const job = await pollJob(created.id);

  let bq = { n: 0, firstImport: null, lastImport: null, freshness: "not checked" };
  try {
    bq = await verifyBigQuery(job);
  } catch (err) {
    console.error(
      "\n⚠️  BigQuery verify query failed:",
      err instanceof Error ? err.message : String(err),
    );
    // Fall back to user ADC / gcloud if the trigger SA lacks bigquery.jobs.create
    try {
      bq = await verifyBigQueryViaGcloud();
    } catch (err2) {
      console.error(
        "⚠️  gcloud bq fallback also failed:",
        err2 instanceof Error ? err2.message : String(err2),
      );
      if (job.status !== "succeeded") {
        printVerdict(job, bq);
      }
      fail("Could not verify BigQuery telemetry rows");
    }
  }

  printVerdict(job, bq);
}

async function verifyBigQueryViaGcloud() {
  console.log("\n── Verify BigQuery via gcloud (fallback) ──");
  const { execFileSync } = await import("node:child_process");
  const project =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const dataset = process.env.BQ_DATASET || "f1_data_library_DS";
  const sql = `
    SELECT COUNT(*) AS n,
           CAST(MIN(imported_at) AS STRING) AS first_import,
           CAST(MAX(imported_at) AS STRING) AS last_import
    FROM \`${project}.${dataset}.telemetry\`
    WHERE season = ${JOB_PARAMS.years[0]}
      AND event_name = '${JOB_PARAMS.race}'
      AND session_type = '${JOB_PARAMS.sessions[0]}'
  `;
  const out = execFileSync(
    "bq",
    [
      "query",
      "--project_id=" + project,
      "--use_legacy_sql=false",
      "--format=json",
      sql,
    ],
    { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 },
  );
  const rows = JSON.parse(out || "[]");
  const row = rows[0] || {};
  const n = Number(row.n || 0);
  console.log(`  rows:         ${n.toLocaleString()}`);
  console.log(`  first_import: ${row.first_import ?? "—"}`);
  console.log(`  last_import:  ${row.last_import ?? "—"}`);
  return {
    n,
    firstImport: row.first_import || null,
    lastImport: row.last_import || null,
    freshness: "checked via gcloud",
  };
}

main().catch((err) => {
  fail(err instanceof Error ? err.message : String(err), err?.stack);
});
