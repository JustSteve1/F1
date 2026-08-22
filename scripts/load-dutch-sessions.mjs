#!/usr/bin/env node
/**
 * Load Dutch GP 2026 sessions via local Load API, then poll + verify status.
 *
 * Usage:
 *   node --env-file=.env.local scripts/load-dutch-sessions.mjs
 *   BASE_URL=http://localhost:3000 node scripts/load-dutch-sessions.mjs
 *
 * Sessions default: FP1 SQ S Q  (override: SESSIONS=FP1,R)
 */

const BASE = (process.env.BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const RACE = process.env.RACE || "Dutch Grand Prix";
const YEAR = Number(process.env.YEAR || 2026);
const SESSIONS = (process.env.SESSIONS || "FP1,SQ,S,Q")
  .split(/[,\s]+/)
  .map((s) => s.trim())
  .filter(Boolean);
const POLL_MS = Number(process.env.POLL_MS || 8000);
const TIMEOUT_MS = Number(process.env.TIMEOUT_MS || 90 * 60 * 1000);

async function fetchJson(url, init) {
  const res = await fetch(url, {
    ...init,
    signal: AbortSignal.timeout(120_000),
  });
  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { res, data };
}

async function createLoad(session) {
  console.log(`\n── Load ${YEAR} ${RACE} ${session} ──`);
  const { res, data } = await fetchJson(`${BASE}/api/admin/import/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      year: YEAR,
      race: RACE,
      sessions: [session],
      noSkip: false,
      skipQuality: false,
      skipUnified: false,
      includeKaggle: false,
    }),
  });
  if (!res.ok) {
    throw new Error(
      `Load ${session} failed (${res.status}): ${data?.error || JSON.stringify(data)}`,
    );
  }
  if (data.warning) {
    console.warn("  warning:", data.warning);
  }
  console.log(`  jobId:     ${data.jobId}`);
  console.log(`  pollUrl:   ${data.pollUrl}`);
  console.log(`  sessionKey:${data.sessionKeys?.[0]?.sessionKey}`);
  return data;
}

async function pollJob(jobId) {
  const deadline = Date.now() + TIMEOUT_MS;
  let last = "";
  while (Date.now() < deadline) {
    const { res, data } = await fetchJson(`${BASE}/api/admin/jobs/${jobId}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Poll failed (${res.status}): ${data?.error || JSON.stringify(data)}`);
    }
    const job = data.job || data;
    const line = `${job.status} ${job.current_step || ""} ${Math.round(job.progress_pct || 0)}% ${job.status_message || ""}`;
    if (line !== last) {
      console.log(`  [${new Date().toISOString()}] ${line}`);
      last = line;
    }
    if (["succeeded", "failed", "cancelled"].includes(job.status)) {
      if (job.status !== "succeeded") {
        throw new Error(
          `Job ${jobId} ${job.status}: ${job.error || job.status_message || ""}`,
        );
      }
      return job;
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
  throw new Error(`Timed out waiting for job ${jobId}`);
}

async function status() {
  const q = new URLSearchParams({
    year: String(YEAR),
    race: RACE,
    sessions: SESSIONS.join(","),
  });
  const { res, data } = await fetchJson(
    `${BASE}/api/admin/import/status?${q}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw new Error(`Status failed (${res.status}): ${data?.error || JSON.stringify(data)}`);
  }
  return data;
}

async function main() {
  console.log(`Base: ${BASE}`);
  console.log(`Sessions: ${SESSIONS.join(", ")}`);

  console.log("\n── Status before ──");
  try {
    console.log(JSON.stringify(await status(), null, 2));
  } catch (err) {
    console.warn("  (status before failed — continuing)", err.message);
  }

  const results = [];
  for (const session of SESSIONS) {
    const created = await createLoad(session);
    const job = await pollJob(created.jobId);
    results.push({ session, jobId: created.jobId, status: job.status });
  }

  console.log("\n── Status after ──");
  const after = await status();
  console.log(JSON.stringify(after, null, 2));

  console.log("\n══════════════════════════════════════");
  console.log("LOAD VERDICT");
  console.log("══════════════════════════════════════");
  for (const r of results) {
    console.log(`  ${r.session}: ${r.status} (${r.jobId})`);
  }
  console.log(`  sessionsInBigQuery: ${after.sessionsInBigQuery?.join(", ") || "—"}`);
  console.log(`  missingFromRequest: ${after.missingFromRequest?.join(", ") || "—"}`);
  console.log(`  telemetryRows:      ${after.telemetryRows}`);
  console.log(`  lapsRows:           ${after.lapsRows}`);

  const missing = after.missingFromRequest || [];
  if (missing.length) {
    console.error(`\n❌ FAIL — still missing: ${missing.join(", ")}`);
    process.exit(1);
  }
  console.log("\n✅ PASS — all requested sessions present in BigQuery");
}

main().catch((err) => {
  console.error("\n❌ FAIL:", err.message);
  process.exit(1);
});
