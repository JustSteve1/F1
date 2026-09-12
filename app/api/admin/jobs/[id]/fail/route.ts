import { NextResponse } from "next/server";
import { stopCloudRunExecution } from "@/lib/jobs/cloud-run";
import { appendJobLog, forceFailJob, getJob } from "@/lib/jobs/queries";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

export async function POST(request: Request, { params }: Params) {
  try {
    const { id } = await params;
    const existing = await getJob(id);
    if (!existing) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    let reason =
      "Force-failed: worker dead or Cloud Run timed out (zombie job)";
    try {
      const body = (await request.json()) as { reason?: string };
      if (body?.reason && typeof body.reason === "string" && body.reason.trim()) {
        reason = body.reason.trim();
      }
    } catch {
      // empty body is fine
    }

    const job = await forceFailJob(id, reason);
    if (!job) {
      return NextResponse.json(
        { error: "Job not found or not in a fail-able status" },
        { status: 409 },
      );
    }

    const cloudRun = await stopCloudRunExecution(
      existing.cloud_run_execution_name,
    );
    if (cloudRun.attempted) {
      await appendJobLog(
        id,
        cloudRun.detail,
        cloudRun.cancelled || cloudRun.alreadyStopped ? "warn" : "error",
      );
    }

    return NextResponse.json({ job, cloudRun });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to fail job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
