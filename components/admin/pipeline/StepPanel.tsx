import { SampleDataPreview } from "./SampleDataPreview";
import { StatusBadge } from "@/components/admin/jobs/StatusBadge";
import type { PipelineGuideStep } from "@/lib/jobs/pipeline-guide";
import type { JobStepRow } from "@/lib/jobs/types";

export function StepPanel({
  guide,
  liveStep,
  liveMessage,
}: {
  guide: PipelineGuideStep;
  liveStep?: JobStepRow | null;
  /** Override sample caption / show live message instead of mock table */
  liveMessage?: string | null;
}) {
  return (
    <div className="border border-white/10 bg-white/[0.02] p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-bold text-white tracking-tight">
              {guide.label}
            </h3>
            {guide.notebookCell && (
              <span className="rounded-sm border border-[#2596be]/40 bg-[#2596be]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#2596be]">
                {guide.notebookCell}
              </span>
            )}
            {liveStep && <StatusBadge status={liveStep.status} />}
          </div>
          <p className="mt-1 text-sm text-white/55">{guide.short}</p>
        </div>
      </div>

      <p className="text-sm text-white/70 leading-relaxed">{guide.detail}</p>

      <div className="grid gap-4 sm:grid-cols-2">
        <ChipGroup label="Inputs" items={guide.inputs} />
        <ChipGroup label="Outputs" items={guide.outputs} />
      </div>

      {guide.writes.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">
            Writes to BigQuery
          </p>
          <div className="flex flex-wrap gap-2">
            {guide.writes.map((table) => (
              <span
                key={table}
                className="rounded-sm border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 font-mono text-[11px] text-emerald-300"
              >
                {table}
              </span>
            ))}
          </div>
        </div>
      )}

      {liveStep && (
        <div className="border border-white/10 px-3 py-2 space-y-1 text-xs text-white/50">
          {liveStep.message && (
            <p>
              <span className="text-white/35">Message · </span>
              {liveStep.message}
            </p>
          )}
          {liveStep.started_at && (
            <p>
              <span className="text-white/35">Started · </span>
              {new Date(liveStep.started_at).toLocaleString()}
            </p>
          )}
          {liveStep.finished_at && (
            <p>
              <span className="text-white/35">Finished · </span>
              {new Date(liveStep.finished_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {liveMessage ? (
        <div className="border border-white/10 px-3 py-2 font-mono text-[11px] text-white/60 whitespace-pre-wrap">
          {liveMessage}
        </div>
      ) : (
        <SampleDataPreview sample={guide.sample} caption="Sample data" />
      )}
    </div>
  );
}

function ChipGroup({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">
        {label}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className="rounded-sm border border-white/15 px-2 py-1 text-[11px] text-white/65"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
