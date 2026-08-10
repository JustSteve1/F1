import { NextResponse } from "next/server";
import { loadImportCatalog } from "@/lib/jobs/import-catalog";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

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
    const catalog = await loadImportCatalog(year, race);
    return NextResponse.json(catalog);
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to load import catalog";
    const status =
      message.toLowerCase().includes("not found") ||
      message.toLowerCase().includes("required")
        ? 400
        : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
