"use client";

import { useEffect, useState } from "react";
import {
  describeHeartbeat,
  formatAge,
  type HeartbeatHealth,
} from "@/lib/jobs/heartbeat";
import { executionShortName } from "@/lib/jobs/cloud-run-names";

const DOT: Record<HeartbeatHealth, string> = {
  idle: "bg-white/30",
  live: "bg-emerald-400 animate-pulse",
  lagging: "bg-amber-400",
  silent: "bg-red-500",
};

export function HeartbeatMeter({
  status,
  updatedAt,
  executionName,
  stepStartedAt,
  compact = false,
}: {
  status: string;
  updatedAt: string;
  executionName?: string | null;
  stepStartedAt?: string | null;
  compact?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const beat = describeHeartbeat({ status, updatedAt, now });
  const short = executionShortName(executionName ?? null);
  const stepMs =
    stepStartedAt && beat.health !== "idle"
      ? Math.max(0, now - Date.parse(stepStartedAt))
      : null;

  if (compact) {
    if (beat.health === "idle") return null;
    return (
      <p
        className={`mt-1 truncate text-[10px] uppercase tracking-widest ${
          beat.health === "live"
            ? "text-emerald-400/80"
            : beat.health === "lagging"
              ? "text-amber-300/80"
              : "text-red-400/80"
        }`}
      >
        <span
          className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${DOT[beat.health]}`}
        />
        {beat.label}
      </p>
    );
  }

  return (
    <div className="space-y-1 text-right">
      <div className="flex items-center justify-end gap-2 text-[11px] text-white/55">
        <span
          className={`inline-block h-2 w-2 rounded-full ${DOT[beat.health]}`}
        />
        <span>{beat.label}</span>
      </div>
      {stepMs != null && Number.isFinite(stepMs) && (
        <p className="text-[10px] uppercase tracking-widest text-white/35">
          Step elapsed {formatAge(stepMs)}
        </p>
      )}
      {short && (
        <p
          className="max-w-[16rem] truncate font-mono text-[10px] text-white/30"
          title={executionName ?? undefined}
        >
          {short}
        </p>
      )}
    </div>
  );
}

export function StaleHeartbeatBanner({
  status,
  updatedAt,
}: {
  status: string;
  updatedAt: string;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const beat = describeHeartbeat({ status, updatedAt, now });
  if (beat.health !== "silent") return null;

  return (
    <p className="mt-2 text-sm text-red-200/90 border border-red-500/30 bg-red-500/10 px-3 py-2 text-left">
      No heartbeat for {formatAge(beat.ageMs)} — worker likely dead. Cancel
      stops Cloud Run; Force fail unblocks Retry.
    </p>
  );
}
