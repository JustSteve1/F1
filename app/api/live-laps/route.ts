import { readFile } from "fs/promises";
import os from "os";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function lapsPath(): string {
  const directory =
    process.env.INTERVAL_LIVE_DIR ||
    path.join(os.homedir(), ".local", "share", "interval", "live");
  return path.join(directory, "live-laps.json");
}

export async function GET() {
  try {
    const raw = await readFile(lapsPath(), "utf8");
    const payload = JSON.parse(raw) as { laps?: unknown };
    const laps = Array.isArray(payload.laps) ? payload.laps : [];
    return NextResponse.json(
      { available: true, laps },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    const missing = (error as NodeJS.ErrnoException).code === "ENOENT";
    return NextResponse.json(
      {
        available: false,
        laps: [],
        error: missing
          ? "No completed laps yet."
          : "The live lap file could not be read.",
      },
      { status: missing ? 200 : 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
