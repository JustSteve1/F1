"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { StatusBadge } from "./StatusBadge";
import { HeartbeatMeter, StaleHeartbeatBanner } from "./HeartbeatMeter";
import { PipelineFlow } from "@/components/admin/pipeline/PipelineFlow";
import { StepPanel } from "@/components/admin/pipeline/StepPanel";
import { guideForKey } from "@/lib/jobs/pipeline-guide";
import { PIPELINE_STEPS } from "@/lib/jobs/steps";
import type { JobDetail as JobDetailType } from "@/lib/jobs/types";

export function JobDetail({
  job,
  onCancel,
  onRetry,
  onFail,
  busy,
}: {
  job: JobDetailType;
  onCancel: () => void;
  onRetry: () => void;
  onFail: () => void;
  busy?: boolean;
}) {
  const logRef = useRef<HTMLDivElement>(null);
  const [pickedKey, setPickedKey] = useState<string | null>(null);
  const [failArmed, setFailArmed] = useState(false);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [job.logs]);

  const followKey =
    job.current_step ||
    job.steps.find((s) => s.status === "running")?.step_key ||
    job.steps[0]?.step_key ||
    null;
  const selectedKey = pickedKey ?? followKey;

  const selectedGuide = useMemo(
    () => (selectedKey ? guideForKey(selectedKey) : undefined),
    [selectedKey],
  );
  const selectedLive = useMemo(
    () => job.steps.find((s) => s.step_key === selectedKey) ?? null,
    [job.steps, selectedKey],
  );

  const active =
    job.status === "queued" ||
    job.status === "running" ||
    job.status === "cancelling";
  const canCancel = active;
  const canFail = active;
  const canRetry = job.status === "failed" || job.status === "cancelled";

  const runningStep = useMemo(
    () =>
      job.steps.find((s) => s.status === "running") ||
      job.steps.find((s) => s.step_key === job.current_step) ||
      null,
    [job.steps, job.current_step],
  );

  const sessionSummary = useMemo(() => {
    const labels = job.params.sessionLabels ?? {};
    return job.params.sessions
      .map((code) => (labels[code] ? `${code} (${labels[code]})` : code))
      .join(" · ");
  }, [job.params.sessionLabels, job.params.sessions]);

  const softFailHint = useMemo(() => {
    const err = job.error || "";
    return (
      /DataNotLoadedError/i.test(err) ||
      /laps unavailable after load/i.test(err)
    );
  }, [job.error]);

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
            {job.params.years.join(", ")} · {sessionSummary}
            {job.params.includeKaggle ? " · Kaggle" : ""}
            {job.params.noSkip ? " · no-skip" : ""}
          </p>
          <p className="mt-2 text-sm text-white/80">
            {job.status_message || "—"}
          </p>
          <StaleHeartbeatBanner
            status={job.status}
            updatedAt={job.updated_at}
          />
          {job.error && (
            <p className="mt-2 text-sm text-red-400 border border-red-500/30 bg-red-500/10 px-3 py-2">
              {job.error}
            </p>
          )}
          {softFailHint && canRetry && (
            <p className="mt-2 text-sm text-amber-200/90 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
              FastF1 soft-fail loading laps — the session id is usually fine.
              Retry often succeeds once the timing API responds.
            </p>
          )}
          {job.status === "cancelling" && (
            <p className="mt-2 text-sm text-amber-200/90 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
              Cancel sent to Cloud Run. The task gets SIGTERM; this row
              flips to cancelled when the execution stops. Force fail if it
              stays here.
            </p>
          )}
        </div>

        <div className="text-right space-y-3">
          <p className="text-[10px] uppercase tracking-widest text-white/35">
            Pipeline
          </p>
          <div className="text-3xl font-black tabular-nums text-[#2596be]">
            {Math.round(job.progress_pct)}%
          </div>
          <p className="text-[11px] text-white/50">
            {PIPELINE_STEPS.find((s) => s.key === job.current_step)?.label ||
              job.current_step ||
              "Queued"}
          </p>
          <div className="ml-auto h-1.5 w-32 overflow-hidden bg-white/10">
            <div
              className="h-full bg-[#2596be] transition-all duration-500"
              style={{ width: `${Math.min(100, job.progress_pct)}%` }}
            />
          </div>
          <HeartbeatMeter
            status={job.status}
            updatedAt={job.updated_at}
            executionName={job.cloud_run_execution_name}
            stepStartedAt={runningStep?.started_at}
          />
          <div className="flex flex-wrap gap-2 justify-end">
            {canCancel && (
              <button
                onClick={onCancel}
                disabled={busy}
                className="border border-amber-400/40 px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest text-amber-300 hover:bg-amber-400/10 disabled:opacity-50"
              >
                {job.status === "cancelling" ? "Retry stop" : "Cancel"}
              </button>
            )}
            {canFail && (
              <button
                onClick={() => {
                  if (!failArmed) {
                    setFailArmed(true);
                    return;
                  }
                  onFail();
                }}
                disabled={busy}
                className="border border-red-500/50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-widest text-red-400 hover:bg-red-500/10 disabled:opacity-50"
              >
                {failArmed ? "Confirm fail" : "Force fail"}
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

      <div className="border border-white/10 p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Pipeline flow
          </h3>
          <p className="text-[10px] text-white/30 uppercase tracking-widest">
            Click a step for notebook mapping
          </p>
        </div>
        <PipelineFlow
          mode="live"
          includeBookends
          steps={job.steps}
          currentStep={job.current_step}
          selectedKey={selectedKey}
          onSelect={(key) => {
            setPickedKey(key);
          }}
        />
        {selectedGuide && (
          <StepPanel guide={selectedGuide} liveStep={selectedLive} />
        )}
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
