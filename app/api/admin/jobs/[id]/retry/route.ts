import { NextResponse } from "next/server";
import { createJob, getJob } from "@/lib/jobs/queries";
import { triggerWorker } from "@/lib/jobs/cloud-run";
import { appendJobLog } from "@/lib/jobs/queries";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

export async function POST(_request: Request, { params }: Params) {
  try {
    const { id } = await params;
    const existing = await getJob(id);
    if (!existing) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    if (!["failed", "cancelled"].includes(existing.status)) {
      return NextResponse.json(
        { error: "Only failed or cancelled jobs can be retried" },
        { status: 409 },
      );
    }

    const job = await createJob(existing.params);
    await appendJobLog(
      job.id,
      `Retry of job ${existing.id} (rerun from start)`,
    );

    try {
      await triggerWorker(job.id);
    } catch (triggerErr) {
      const message =
        triggerErr instanceof Error
          ? triggerErr.message
          : "Failed to trigger worker";
      return NextResponse.json(
        {
          job,
          warning: `Retry job created but worker trigger failed: ${message}`,
        },
        { status: 201 },
      );
    }

    return NextResponse.json({ job }, { status: 201 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to retry job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
