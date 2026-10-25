"use client";

import { useEffect, useState } from "react";

type SessionView = {
  event?: string;
  code?: string;
  label?: string;
  starts_at?: string;
  record_from?: string;
  record_until?: string;
  stop_reason?: string;
  laps?: number;
};

type TokenView = {
  state?: "valid" | "expiring" | "expired" | "missing" | string;
  expires_at?: string | null;
  seconds_left?: number | null;
  subscribed_product?: string | null;
  renewable?: boolean;
  action?: string;
  error?: string | null;
};

type WatcherView = {
  updated_at?: string;
  state?: string;
  next_session?: SessionView | null;
  session?: SessionView | null;
  last_session?: SessionView | null;
  subscriber?: { pid?: number; restarts?: number; session_status?: string | null } | null;
  error?: string;
};

type EventView = {
  at: string;
  level: "info" | "warning" | "error";
  title: string;
  message?: string;
};

type StatusPayload = {
  available: boolean;
  watcher: WatcherView | null;
  token: TokenView | null;
  events: EventView[];
};

function duration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const days = Math.floor(total / 86400);
  const hours = Math.floor((total % 86400) / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function when(iso: string | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

function tokenTone(state: string | undefined): string {
  if (state === "valid") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-300";
  if (state === "expiring") return "border-yellow-400/40 bg-yellow-400/15 text-yellow-200";
  return "border-red-500/40 bg-red-500/15 text-red-300";
}

function watcherTone(state: string | undefined): string {
  if (state === "recording") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-300";
  if (state === "armed" || state === "between_sessions") return "border-white/15 bg-white/5 text-white/70";
  if (!state) return "border-white/15 bg-white/5 text-white/40";
  return "border-yellow-400/40 bg-yellow-400/15 text-yellow-200";
}

function watcherLabel(state: string | undefined): string {
  switch (state) {
    case "recording":
      return "Recording";
    case "armed":
      return "Armed";
    case "between_sessions":
      return "Waiting";
    case "waiting_for_sign_in":
      return "Sign-in needed";
    case "idle":
      return "No sessions";
    case "stopped":
      return "Watcher stopped";
    case "error":
      return "Watcher error";
    default:
      return "Watcher offline";
  }
}

export function LiveStatusStrip() {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const response = await fetch("/api/live-status", { cache: "no-store" });
        if (!response.ok) return;
        const body = (await response.json()) as StatusPayload;
        if (!cancelled) setData(body);
      } catch {
        // The timing board reports feed errors; this strip stays quiet.
      }
    }
    load();
    const poll = window.setInterval(load, 10_000);
    const tick = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearInterval(tick);
    };
  }, []);

  const watcher = data?.watcher ?? null;
  const token = data?.token ?? null;
  const events = data?.events ?? [];

  const watcherStale =
    !!watcher?.updated_at && now - Date.parse(watcher.updated_at) > 15 * 60 * 1000;
  const watcherState = watcherStale ? undefined : watcher?.state;
  const target = watcher?.session ?? watcher?.next_session ?? null;
  const expiresAt = token?.expires_at ? Date.parse(token.expires_at) : null;
  const tokenLeft = expiresAt !== null ? expiresAt - now : null;
  const tokenState =
    tokenLeft === null ? token?.state : tokenLeft <= 0 ? "expired" : tokenLeft <= 24 * 3600 * 1000 ? "expiring" : "valid";
  const latest = events[0];

  return (
    <div className="mb-6 rounded-sm border border-white/10 bg-white/[0.03] px-4 py-3 text-white">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${watcherTone(watcherState)}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${watcherState === "recording" ? "bg-emerald-400" : "bg-white/30"}`} />
          {watcherLabel(watcherState)}
        </span>

        <span className="font-mono text-xs text-white/70">
          {watcherState === "recording" && target ? (
            <>
              {target.event} · {target.label}
              {watcher?.subscriber?.session_status ? ` · ${watcher.subscriber.session_status}` : ""}
              {watcher?.subscriber?.restarts ? ` · ${watcher.subscriber.restarts} reconnect(s)` : ""}
            </>
          ) : watcherState === "armed" && target?.record_from ? (
            <>
              Next: {target.event} · {target.label} · session {when(target.starts_at)} · recording starts in{" "}
              {duration(Date.parse(target.record_from) - now)}
            </>
          ) : watcherState === "between_sessions" && watcher?.last_session ? (
            <>
              Last: {watcher.last_session.event} · {watcher.last_session.label}
              {typeof watcher.last_session.laps === "number" ? ` · ${watcher.last_session.laps} laps` : ""}
            </>
          ) : watcherState === "waiting_for_sign_in" ? (
            <>A session window is open but there is no usable subscription token.</>
          ) : watcher?.error ? (
            <>{watcher.error}</>
          ) : (
            <>python3 worker/pipeline/live_watch.py</>
          )}
        </span>

        <span className="ml-auto inline-flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider ${tokenTone(tokenState)}`}
          >
            Token {tokenState ?? "unknown"}
          </span>
          <span className="font-mono text-xs text-white/60">
            {tokenLeft !== null && tokenLeft > 0
              ? `${duration(tokenLeft)} left · ${when(token?.expires_at ?? undefined)}`
              : token?.state === "missing" || !token
                ? "no token on this machine"
                : "expired"}
            {token?.renewable === false && token?.state !== "missing" ? " · not renewable" : ""}
          </span>
        </span>
      </div>

      {latest ? (
        <p
          className={`mt-2 font-mono text-[11px] ${
            latest.level === "error"
              ? "text-red-300"
              : latest.level === "warning"
                ? "text-yellow-200"
                : "text-white/45"
          }`}
        >
          {when(latest.at)} · {latest.title}
          {latest.message ? ` — ${latest.message}` : ""}
        </p>
      ) : null}
    </div>
  );
}
