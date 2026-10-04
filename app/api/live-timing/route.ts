import { readFile } from "fs/promises";
import os from "os";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function snapshotPath(): string {
  const directory =
    process.env.INTERVAL_LIVE_DIR ||
    path.join(os.homedir(), ".local", "share", "interval", "live");
  return path.join(directory, "timing-snapshot.json");
}

export async function GET() {
  try {
    const raw = await readFile(snapshotPath(), "utf8");
    const snapshot = JSON.parse(raw) as Record<string, unknown>;
    return NextResponse.json(
      { available: true, ...snapshot },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    const missing = (error as NodeJS.ErrnoException).code === "ENOENT";
    return NextResponse.json(
      {
        available: false,
        error: missing
          ? "No live snapshot yet."
          : "The live snapshot could not be read.",
      },
      { status: missing ? 200 : 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
