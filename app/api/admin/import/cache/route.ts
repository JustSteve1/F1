import { NextResponse } from "next/server";
import { fetchFastf1Cache } from "@/lib/jobs/fastf1-cache";
import { SESSION_TYPES, type SessionType } from "@/lib/jobs/steps";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function parseRequestedSessions(raw: string | null): SessionType[] | undefined {
  if (!raw?.trim()) return undefined;
  const codes = raw
    .split(/[,\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const valid = codes.filter((c): c is SessionType =>
    (SESSION_TYPES as readonly string[]).includes(c),
  );
  return valid.length ? valid : undefined;
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const yearRaw = searchParams.get("year");
    const year = Number(yearRaw);
    if (!yearRaw || !Number.isFinite(year)) {
      return NextResponse.json(
        { error: "Query param year is required (e.g. ?year=2026)" },
        { status: 400 },
      );
    }

    const race = searchParams.get("race")?.trim() || undefined;
    const requestedSessions = parseRequestedSessions(
      searchParams.get("sessions"),
    );

    const status = await fetchFastf1Cache({
      year,
      race,
      requestedSessions,
    });
    return NextResponse.json(status);
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to list FastF1 cache";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
