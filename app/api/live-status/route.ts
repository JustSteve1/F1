import { readFile } from "fs/promises";
import os from "os";
import path from "path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Mirrors notify.live_dir() and live_token.status_path() in worker/pipeline.
function liveDir(): string {
  return (
    process.env.INTERVAL_LIVE_DIR ||
    path.join(os.homedir(), ".local", "share", "interval", "live")
  );
}

function tokenStatusPath(): string {
  const tokenFile =
    process.env.F1_SUBSCRIPTION_TOKEN_FILE ||
    path.join(os.homedir(), ".config", "interval", "f1-subscription-token");
  return `${tokenFile}.status.json`;
}

async function readJson(file: string): Promise<Record<string, unknown> | null> {
  try {
    return JSON.parse(await readFile(file, "utf8")) as Record<string, unknown>;
  } catch {
    return null;
  }
}

async function readEvents(file: string, limit: number): Promise<Record<string, unknown>[]> {
  try {
    const raw = await readFile(file, "utf8");
    return raw
      .split("\n")
      .filter((line) => line.trim())
      .slice(-limit)
      .flatMap((line) => {
        try {
          return [JSON.parse(line) as Record<string, unknown>];
        } catch {
          return [];
        }
      })
      .reverse();
  } catch {
    return [];
  }
}

export async function GET() {
  const directory = liveDir();
  const [watcher, token, events] = await Promise.all([
    readJson(path.join(directory, "watcher-status.json")),
    readJson(tokenStatusPath()),
    readEvents(path.join(directory, "events.jsonl"), 8),
  ]);
  return NextResponse.json(
    {
      available: watcher !== null || token !== null,
      watcher,
      // The watcher embeds the token record it last saw; the file is fresher.
      token: token ?? (watcher?.token as Record<string, unknown> | null) ?? null,
      events,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
