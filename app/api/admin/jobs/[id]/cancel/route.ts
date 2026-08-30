import { NextResponse } from "next/server";
import { stopCloudRunExecution } from "@/lib/jobs/cloud-run";
import {
  appendJobLog,
  finalizeCancel,
  requestCancel,
} from "@/lib/jobs/queries";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  try {
    const { id } = await params;
    const job = await requestCancel(id);
    if (!job) {
      return NextResponse.json(
        { error: "Job not found or not cancellable" },
        { status: 409 },
      );
    }

    const cloudRun = await stopCloudRunExecution(job.cloud_run_execution_name);
    await appendJobLog(
      id,
      cloudRun.detail,
      cloudRun.cancelled || cloudRun.alreadyStopped ? "warn" : "error",
    );

    // Stub/local, missing execution, or already-dead Cloud Run: finalize now.
    // A live cancel leaves status=cancelling until SIGTERM / reconcile.
    let next = job;
    if (cloudRun.alreadyStopped || !cloudRun.attempted) {
      const finalized = await finalizeCancel(id, "Cancelled");
      if (finalized) next = finalized;
    }

    return NextResponse.json({ job: next, cloudRun });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to cancel job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
