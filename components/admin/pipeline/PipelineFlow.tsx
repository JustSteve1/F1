"use client";

import { StatusBadge } from "@/components/admin/jobs/StatusBadge";
import { cn } from "@/lib/utils";
import {
  PIPELINE_GUIDE,
  PIPELINE_GUIDE_RAIL,
  type PipelineGuideStep,
} from "@/lib/jobs/pipeline-guide";
import { PIPELINE_STEPS, stepsForParams, type JobParams } from "@/lib/jobs/steps";
import type { JobStepRow } from "@/lib/jobs/types";

export type PipelineFlowMode = "guide" | "live" | "preview";

type Props = {
  mode: PipelineFlowMode;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  /** live mode */
  steps?: JobStepRow[];
  currentStep?: string | null;
  /** preview mode — mute steps not in stepsForParams */
  params?: Pick<
    JobParams,
    "skipQuality" | "skipUnified" | "includeKaggle"
  > &
    Partial<JobParams>;
  className?: string;
  /** Include queued/done bookends (live jobs often have them) */
  includeBookends?: boolean;
};

function railSteps(
  mode: PipelineFlowMode,
  includeBookends: boolean,
): PipelineGuideStep[] {
  if (mode === "guide") {
    return includeBookends
      ? PIPELINE_STEPS.map((s) => PIPELINE_GUIDE[s.key])
      : PIPELINE_GUIDE_RAIL;
  }
  // live / preview: full pipeline order from PIPELINE_STEPS
  const all = PIPELINE_STEPS.map((s) => PIPELINE_GUIDE[s.key]);
  if (includeBookends) return all;
  return all.filter((s) => s.key !== "queued" && s.key !== "done");
}

export function PipelineFlow({
  mode,
  selectedKey,
  onSelect,
  steps = [],
  currentStep,
  params,
  className,
  includeBookends = false,
}: Props) {
  const rail = railSteps(mode, includeBookends);
  const stepByKey = Object.fromEntries(steps.map((s) => [s.step_key, s]));

  const activeKeys =
    mode === "preview" && params
      ? new Set(
          stepsForParams({
            years: params.years ?? [2025],
            race: params.race ?? "",
            sessions: params.sessions ?? ["R"],
            noSkip: params.noSkip ?? false,
            skipQuality: params.skipQuality,
            skipUnified: params.skipUnified,
            includeKaggle: params.includeKaggle,
          }).map((s) => s.key),
        )
      : null;

  return (
    <div className={cn("w-full", className)}>
      <ol
        className={cn(
          "flex flex-col gap-2",
          "md:flex-row md:flex-wrap md:items-stretch md:gap-1",
        )}
      >
        {rail.map((guide, index) => {
          const live = stepByKey[guide.key];
          const muted =
            mode === "preview" && activeKeys
              ? !activeKeys.has(guide.key)
              : live?.status === "skipped";
          const selected = selectedKey === guide.key;
          const isCurrent =
            mode === "live" &&
            (currentStep === guide.key || live?.status === "running");

          return (
            <li
              key={guide.key}
              className={cn(
                "relative flex md:min-w-[7.5rem] md:max-w-[9.5rem] md:flex-1",
                index < rail.length - 1 && "md:pr-2",
              )}
            >
              <button
                type="button"
                disabled={!onSelect}
                onClick={() => onSelect?.(guide.key)}
                className={cn(
                  "w-full border px-2.5 py-2 text-left transition-colors",
                  "disabled:cursor-default",
                  muted && "opacity-35",
                  selected
                    ? "border-[#2596be] bg-[#2596be]/15"
                    : isCurrent
                      ? "border-[#2596be]/60 bg-[#2596be]/10"
                      : "border-white/10 bg-white/[0.02] hover:border-white/25",
                  onSelect && !selected && "hover:bg-white/[0.04]",
                )}
              >
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[9px] font-bold uppercase tracking-widest text-white/35">
                    {guide.notebookCell ?? (mode === "live" || mode === "preview" ? "—" : "App")}
                  </span>
                  {mode === "live" && live && (
                    <StatusBadge status={live.status} className="scale-90 origin-right" />
                  )}
                  {mode === "preview" && muted && (
                    <span className="text-[9px] uppercase tracking-widest text-white/30">
                      skip
                    </span>
                  )}
                </div>
                <p
                  className={cn(
                    "mt-1 text-[11px] font-semibold leading-snug",
                    selected || isCurrent ? "text-white" : "text-white/75",
                  )}
                >
                  {guide.label}
                </p>
              </button>
              {index < rail.length - 1 && (
                <span
                  aria-hidden
                  className="pointer-events-none absolute right-0 top-1/2 hidden h-px w-2 -translate-y-1/2 bg-white/20 md:block"
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
