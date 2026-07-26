import { cn } from "@/lib/utils";
import type { JobStatus, JobStepStatus } from "@/lib/jobs/steps";

const STATUS_STYLES: Record<string, string> = {
  queued: "border-white/20 text-white/70",
  pending: "border-white/20 text-white/50",
  running: "border-[#2596be] text-[#2596be]",
  cancelling: "border-amber-400/60 text-amber-300",
  cancelled: "border-white/30 text-white/50",
  succeeded: "border-emerald-500/50 text-emerald-400",
  failed: "border-red-500/60 text-red-400",
  skipped: "border-white/15 text-white/40",
};

export function StatusBadge({
  status,
  className,
}: {
  status: JobStatus | JobStepStatus | string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest",
        STATUS_STYLES[status] ?? "border-white/20 text-white/60",
        className,
      )}
    >
      {status}
    </span>
  );
}
