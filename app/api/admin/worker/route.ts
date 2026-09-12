import { NextResponse } from "next/server";
import { getWorkerInfo } from "@/lib/jobs/worker-info";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(getWorkerInfo());
}
