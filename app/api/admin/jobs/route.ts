import { NextResponse } from "next/server";
import { createJob, listJobs, parseJobParams } from "@/lib/jobs/queries";
import { triggerWorker } from "@/lib/jobs/cloud-run";
import { validateJobParamsAgainstCatalog } from "@/lib/jobs/import-catalog";
import { reconcileActiveJobs } from "@/lib/jobs/reconcile";
import { getWorkerInfo } from "@/lib/jobs/worker-info";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    let jobs = await listJobs(100);
    if (await reconcileActiveJobs(jobs)) {
      jobs = await listJobs(100);
    }
    return NextResponse.json({ jobs, worker: getWorkerInfo() });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to list jobs";
    return NextResponse.json(
      { error: message, worker: getWorkerInfo() },
      { status: 500 },
    );
  }
}

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
      // Job row exists; surface trigger failure without losing the create.
      return NextResponse.json(
        {
          job,
          warning: `Job created but worker trigger failed: ${message}`,
        },
        { status: 201 },
      );
    }

    return NextResponse.json({ job }, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create job";
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
