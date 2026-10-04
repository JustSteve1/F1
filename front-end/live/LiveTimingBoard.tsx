"use client";

import { useEffect, useState } from "react";

type DriverRow = {
  driver_number: string;
  tla: string | null;
  position: string | null;
  gap: string | null;
  interval: string | null;
  last_lap: string | null;
  sector1: string | null;
  sector2: string | null;
  sector3: string | null;
  status: string | null;
};

type LivePayload = {
  available: boolean;
  error?: string;
  updated_at?: string;
  session?: {
    name?: string | null;
    type?: string | null;
    meeting?: string | null;
    status?: string | null;
  };
  clock?: {
    Remaining?: string;
    Utc?: string;
  };
  track_status?: { Status?: string; Message?: string } | null;
  lap_count?: { CurrentLap?: number } | null;
  drivers?: DriverRow[];
};

function text(value: unknown): string {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  return "—";
}

function trackTone(message: string | undefined): string {
  const name = (message || "").toLowerCase();
  if (name.includes("red") || name.includes("sc") || name.includes("vsc")) {
    return "border-red-500/40 bg-red-500/15 text-red-300";
  }
  if (name.includes("yellow")) {
    return "border-yellow-400/40 bg-yellow-400/15 text-yellow-200";
  }
  if (name.includes("clear") || name.includes("green")) {
    return "border-emerald-400/40 bg-emerald-400/15 text-emerald-300";
  }
  return "border-white/15 bg-white/5 text-white/70";
}

function rowClass(status: string | null): string {
  if (status === "retired" || status === "out" || status === "stopped") {
    return "text-white/35";
  }
  if (status === "pit" || status === "pit_out") {
    return "bg-yellow-400/[0.06]";
  }
  return "";
}

export function LiveTimingBoard() {
  const [data, setData] = useState<LivePayload | null>(null);
  const [ageMs, setAgeMs] = useState<number | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch("/api/live-timing", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const body = (await response.json()) as LivePayload;
        if (!cancelled) {
          setData(body);
          setFetchError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setFetchError(error instanceof Error ? error.message : "Request failed");
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

  useEffect(() => {
    if (!data?.updated_at) {
      setAgeMs(null);
      return;
    }
    const stamp = data.updated_at;
    const compute = () => setAgeMs(Date.now() - Date.parse(stamp));
    compute();
    const tick = window.setInterval(compute, 250);
    return () => window.clearInterval(tick);
  }, [data?.updated_at]);

  const live = ageMs !== null && ageMs < 4000;
  const session = data?.session;
  const drivers = data?.drivers ?? [];
  const lap = data?.lap_count?.CurrentLap;
  const remaining = data?.clock?.Remaining;
  const track = data?.track_status?.Message;

  return (
    <div className="text-white">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${
                live
                  ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
                  : "border-white/15 bg-white/5 text-white/50"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald-400" : "bg-white/30"}`} />
              {live ? "Live" : "Idle"}
            </span>
            {session?.status ? (
              <span className="font-mono text-[11px] uppercase tracking-wider text-white/45">
                {session.status}
              </span>
            ) : null}
          </div>
          <h1 className="text-3xl font-black uppercase tracking-tighter md:text-4xl">
            {session?.meeting || "Live timing"}
          </h1>
          <p className="mt-1 font-mono text-xs uppercase tracking-widest text-white/45">
            {[session?.name, session?.type].filter(Boolean).join(" · ") || "Waiting for a session"}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Stat label="Lap" value={lap != null ? String(lap) : "—"} />
          <Stat label="Remaining" value={text(remaining)} />
          <span className={`inline-flex min-w-[7rem] flex-col rounded-sm border px-3 py-2 ${trackTone(track)}`}>
            <span className="font-mono text-[10px] uppercase tracking-widest opacity-70">Track</span>
            <span className="font-mono text-sm font-semibold">{text(track)}</span>
          </span>
        </div>
      </div>

      {fetchError ? (
        <p className="mb-4 font-mono text-sm text-red-300">Feed request failed: {fetchError}</p>
      ) : null}

      {!data?.available ? (
        <div className="rounded-sm border border-white/10 bg-white/[0.03] p-8">
          <p className="text-sm text-white/70">
            {data?.error || "No live snapshot yet."}
          </p>
          <p className="mt-3 font-mono text-xs text-white/40">
            python3 worker/pipeline/live_subscriber.py
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-sm border border-white/10">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="bg-white/[0.04] font-mono text-[10px] uppercase tracking-widest text-white/40">
              <tr>
                <th className="px-3 py-2 font-medium">Pos</th>
                <th className="px-3 py-2 font-medium">No</th>
                <th className="px-3 py-2 font-medium">Driver</th>
                <th className="px-3 py-2 font-medium">Gap</th>
                <th className="px-3 py-2 font-medium">Int</th>
                <th className="px-3 py-2 font-medium">Last</th>
                <th className="px-3 py-2 font-medium">S1</th>
                <th className="px-3 py-2 font-medium">S2</th>
                <th className="px-3 py-2 font-medium">S3</th>
              </tr>
            </thead>
            <tbody className="font-mono text-sm">
              {drivers.map((driver) => (
                <tr
                  key={driver.driver_number}
                  className={`border-t border-white/10 ${rowClass(driver.status)}`}
                >
                  <td className="px-3 py-2 font-semibold text-white">{text(driver.position)}</td>
                  <td className="px-3 py-2 text-white/50">{driver.driver_number}</td>
                  <td className="px-3 py-2 font-semibold tracking-wide">
                    {text(driver.tla)}
                    {driver.status && driver.status !== "on_track" ? (
                      <span className="ml-2 text-[10px] uppercase tracking-widest text-yellow-200/80">
                        {driver.status.replace("_", " ")}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2">{text(driver.gap)}</td>
                  <td className="px-3 py-2 text-white/70">{text(driver.interval)}</td>
                  <td className="px-3 py-2">{text(driver.last_lap)}</td>
                  <td className="px-3 py-2 text-white/80">{text(driver.sector1)}</td>
                  <td className="px-3 py-2 text-white/80">{text(driver.sector2)}</td>
                  <td className="px-3 py-2 text-white/80">{text(driver.sector3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-3 font-mono text-[11px] text-white/35">
        {data?.updated_at
          ? `Snapshot ${new Date(data.updated_at).toISOString()}${
              ageMs != null ? ` · ${(ageMs / 1000).toFixed(1)}s ago` : ""
            }`
          : "Polling /api/live-timing"}
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex min-w-[6.5rem] flex-col rounded-sm border border-white/10 bg-white/[0.03] px-3 py-2">
      <span className="font-mono text-[10px] uppercase tracking-widest text-white/40">{label}</span>
      <span className="font-mono text-sm font-semibold text-white">{value}</span>
    </span>
  );
}
