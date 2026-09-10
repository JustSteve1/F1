import { NextResponse } from "next/server";
import { triggerWorker } from "@/lib/jobs/cloud-run";
import { validateJobParamsAgainstCatalog } from "@/lib/jobs/import-catalog";
import { createJob, parseJobParams } from "@/lib/jobs/queries";
import { generateSessionKey } from "@/lib/jobs/session-key";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const EXPECTED_TABLES = [
  "sessions",
  "laps",
  "telemetry",
  "laps_unified",
] as const;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const params = parseJobParams(body);
    await validateJobParamsAgainstCatalog(params);
    const job = await createJob(params);

    try {
      await triggerWorker(job.id);
    } catch (triggerErr) {
      const message =
        triggerErr instanceof Error
          ? triggerErr.message
          : "Failed to trigger worker";
      return NextResponse.json(
        {
          jobId: job.id,
          status: job.status,
          pollUrl: `/api/admin/jobs/${job.id}`,
          expectedTables: params.includeKaggle
          ? ["for_kaggle_export"]
          : [...EXPECTED_TABLES],
          sessionKeys: params.years.flatMap((year) =>
            params.sessions.map((session) => ({
              year,
              race: params.race,
              session,
              sessionKey: generateSessionKey(year, params.race, session),
            })),
          ),
          warning: `Job created but worker trigger failed: ${message}`,
        },
        { status: 201 },
      );
    }

    return NextResponse.json(
      {
        jobId: job.id,
        status: job.status,
        pollUrl: `/api/admin/jobs/${job.id}`,
        expectedTables: params.includeKaggle
          ? ["for_kaggle_export"]
          : [...EXPECTED_TABLES],
        sessionKeys: params.years.flatMap((year) =>
          params.sessions.map((session) => ({
            year,
            race: params.race,
            session,
            sessionKey: generateSessionKey(year, params.race, session),
          })),
        ),
      },
      { status: 201 },
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create load job";
    const lower = message.toLowerCase();
    const status =
      lower.includes("required") ||
      lower.includes("not found") ||
      lower.includes("not a session") ||
      lower.includes("invalid")
        ? 400
        : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
