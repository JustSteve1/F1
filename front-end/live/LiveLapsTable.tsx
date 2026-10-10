"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const COLUMNS = [
  "imported_at",
  "season",
  "event_name",
  "session_type",
  "driver_number",
  "driver_code",
  "team",
  "position",
  "lap_number",
  "lap_duration",
  "sector_1_time",
  "sector_2_time",
  "sector_3_time",
  "speed_i1",
  "speed_i2",
  "speed_st",
  "compound",
  "tyre_age_laps",
  "stint_number",
  "fresh_tyre",
  "is_personal_best",
  "track_status",
  "session_key",
] as const;

type LapRow = Record<string, unknown>;

function cell(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

export function LiveLapsTable() {
  const [laps, setLaps] = useState<LapRow[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch("/api/live-laps", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as {
          available?: boolean;
          laps?: LapRow[];
          error?: string;
        };
        if (cancelled) return;
        setLaps(body.laps ?? []);
        setReady(true);
        setError(body.available ? null : body.error || null);
        const newest = body.laps?.[0]?.imported_at;
        setUpdatedAt(typeof newest === "string" ? newest : null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Request failed");
        }
      }
    }

    load();
    const poll = window.setInterval(load, 500);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
    };
  }, []);

  return (
    <div className="text-white">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-white/45">
            laps_live
          </p>
          <h1 className="text-3xl font-black uppercase tracking-tighter md:text-4xl">
            Completed laps
          </h1>
          <p className="mt-1 font-mono text-xs uppercase tracking-widest text-white/45">
            Newest finish first · {laps.length} row{laps.length === 1 ? "" : "s"}
          </p>
        </div>
        <Link
          href="/live"
          className="font-mono text-[11px] uppercase tracking-widest text-white/50 hover:text-white"
        >
          Timing tower
        </Link>
      </div>

      {error && laps.length === 0 ? (
        <div className="rounded-sm border border-white/10 bg-white/[0.03] p-8">
          <p className="text-sm text-white/70">{error}</p>
        </div>
      ) : null}

      {ready && laps.length > 0 ? (
        <div className="overflow-x-auto rounded-sm border border-white/10">
          <table className="w-full min-w-[1400px] border-collapse text-left">
            <thead className="bg-white/[0.04] font-mono text-[10px] uppercase tracking-widest text-white/40">
              <tr>
                {COLUMNS.map((column) => (
                  <th key={column} className="whitespace-nowrap px-3 py-2 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {laps.map((lap, index) => (
                <tr
                  key={`${cell(lap.session_key)}-${cell(lap.driver_number)}-${cell(lap.lap_number)}-${index}`}
                  className="border-t border-white/10"
                >
                  {COLUMNS.map((column) => (
                    <td key={column} className="whitespace-nowrap px-3 py-2 text-white/80">
                      {cell(lap[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="mt-3 font-mono text-[11px] text-white/35">
        {updatedAt ? `Newest lap ${updatedAt}` : "Polling /api/live-laps"}
      </p>
    </div>
  );
}
