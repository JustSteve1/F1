"use client";

import { useEffect, useRef } from "react";
import { StatusBadge } from "./StatusBadge";
import type { JobDetail as JobDetailType } from "@/lib/jobs/types";
import { PIPELINE_STEPS } from "@/lib/jobs/steps";

const STEP_LABELS = Object.fromEntries(
  PIPELINE_STEPS.map((s) => [s.key, s.label]),
);

export function JobDetail({
  job,
  onCancel,
  onRetry,
  busy,
}: {
  job: JobDetailType;
  onCancel: () => void;
  onRetry: () => void;
  busy?: boolean;
}) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [job.logs]);

  const canCancel = job.status === "queued" || job.status === "running";
  const canRetry = job.status === "failed" || job.status === "cancelled";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-4 border border-white/10 bg-white/[0.02] p-5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-white tracking-tight">
              {job.params.race}
            </h2>
            <StatusBadge status={job.status} />
          </div>
          <p className="mt-1 text-xs text-white/45 font-mono">{job.id}</p>
          <p className="mt-2 text-sm text-white/60">
            {job.params.years.join(", ")} · {job.params.sessions.join(" ")}
            {job.params.includeKaggle ? " · Kaggle" : ""}
            {job.params.noSkip ? " · no-skip" : ""}
          </p>
          <p className="mt-2 text-sm text-white/80">
            {job.status_message || "—"}
          </p>
          {job.error && (
            <p className="mt-2 text-sm text-red-400 border border-red-500/30 bg-red-500/10 px-3 py-2">
              {job.error}
            </p>
          )}
        </div>

        <div className="text-right space-y-2">
          <div className="text-3xl font-black tabular-nums text-[#2596be]">
            {Math.round(job.progress_pct)}%
          </div>
          <div className="flex gap-2 justify-end">
            {canCancel && (
              <button
                onClick={onCancel}
                disabled={busy}
                className="border border-amber-400/40 px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest text-amber-300 hover:bg-amber-400/10 disabled:opacity-50"
              >
                Cancel
              </button>
            )}
            {canRetry && (
              <button
                onClick={onRetry}
                disabled={busy}
                className="bg-[#2596be] px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest text-white hover:brightness-110 disabled:opacity-50"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="border border-white/10 p-5">
        <h3 className="text-[11px] font-bold uppercase tracking-widest text-white/50 mb-4">
          Step timeline
        </h3>
        <ol className="space-y-3">
          {job.steps.map((step) => (
            <li key={step.id} className="flex items-start gap-3">
              <StatusBadge status={step.status} className="mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-white">
                  {STEP_LABELS[step.step_key] || step.step_key}
                </p>
                {step.message && (
                  <p className="text-xs text-white/45">{step.message}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="border border-white/10">
        <div className="border-b border-white/10 px-4 py-2 flex items-center justify-between">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Live logs
          </h3>
          <span className="text-[10px] text-white/30 uppercase tracking-widest">
            Auto-scroll
          </span>
        </div>
        <div
          ref={logRef}
          className="h-72 overflow-y-auto bg-black px-4 py-3 font-mono text-[11px] leading-relaxed"
        >
          {job.logs.length === 0 ? (
            <p className="text-white/30">No logs yet…</p>
          ) : (
            job.logs.map((log) => (
              <div key={log.id} className="whitespace-pre-wrap break-words">
                <span className="text-white/30">
                  {new Date(log.ts).toLocaleTimeString()}{" "}
                </span>
                <span
                  className={
                    log.level === "error"
                      ? "text-red-400"
                      : log.level === "warn"
                        ? "text-amber-300"
                        : "text-white/70"
                  }
                >
                  [{log.level}] {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
