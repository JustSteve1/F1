export type HeartbeatHealth = "idle" | "live" | "lagging" | "silent";

/** Worker writes updated_at on this interval. */
export const HEARTBEAT_INTERVAL_MS = 30_000;
/** Alive if a beat arrived within 30s + 15s slack. */
export const HEARTBEAT_LIVE_MS = 45_000;
/** Soft warning before the 15 min watchdog. */
export const HEARTBEAT_LAGGING_MS = 3 * 60_000;
/** Matches lib/jobs/reconcile.ts STALE_MS. */
export const HEARTBEAT_STALE_MS = 15 * 60_000;

const ACTIVE = new Set(["queued", "running", "cancelling"]);

export function formatAge(ms: number): string {
  const sec = Math.max(0, Math.floor(ms / 1000));
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) {
    const rem = sec % 60;
    return rem ? `${min}m ${rem}s` : `${min}m`;
  }
  const hr = Math.floor(min / 60);
  const remMin = min % 60;
  return remMin ? `${hr}h ${remMin}m` : `${hr}h`;
}

export function describeHeartbeat(opts: {
  status: string;
  updatedAt: string;
  now?: number;
}): {
  health: HeartbeatHealth;
  ageMs: number;
  label: string;
  stale: boolean;
} {
  const now = opts.now ?? Date.now();
  const t = Date.parse(opts.updatedAt);
  const ageMs = Number.isFinite(t) ? Math.max(0, now - t) : 0;
  const stale = ageMs >= HEARTBEAT_STALE_MS;

  if (!ACTIVE.has(opts.status)) {
    return { health: "idle", ageMs, label: "Stopped", stale: false };
  }
  if (ageMs <= HEARTBEAT_LIVE_MS) {
    return {
      health: "live",
      ageMs,
      label: `Live · ${formatAge(ageMs)} ago`,
      stale,
    };
  }
  if (ageMs <= HEARTBEAT_LAGGING_MS) {
    return {
      health: "lagging",
      ageMs,
      label: `Lagging · ${formatAge(ageMs)} ago`,
      stale,
    };
  }
  return {
    health: "silent",
    ageMs,
    label: `Silent · ${formatAge(ageMs)} ago`,
    stale,
  };
}
