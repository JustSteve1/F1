import { NextResponse } from "next/server";
import { requestCancel } from "@/lib/jobs/queries";

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
    return NextResponse.json({ job });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to cancel job";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
