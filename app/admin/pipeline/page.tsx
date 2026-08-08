"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { PipelineFlow } from "@/components/admin/pipeline/PipelineFlow";
import { StepPanel } from "@/components/admin/pipeline/StepPanel";
import {
  PIPELINE_GUIDE,
  PIPELINE_GUIDE_RAIL,
  PIPELINE_PRELUDE,
} from "@/lib/jobs/pipeline-guide";

export default function AdminPipelinePage() {
  const demo = PIPELINE_PRELUDE.demoConfig;
  const defaultKey = PIPELINE_GUIDE_RAIL[0]?.key ?? "load_fastf1";
  const [selectedKey, setSelectedKey] = useState<string>(defaultKey);

  const guide = useMemo(
    () => PIPELINE_GUIDE[selectedKey as keyof typeof PIPELINE_GUIDE],
    [selectedKey],
  );

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <Link
              href="/"
              className="text-xl font-bold tracking-tighter text-white"
            >
              Interval.ai
            </Link>
            <p className="mt-0.5 text-[11px] uppercase tracking-widest text-white/40">
              Admin · Pipeline guide
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <Link
              href="/admin/jobs"
              className="text-white/50 hover:text-white transition-colors"
            >
              Pipeline jobs
            </Link>
            <span className="text-[#2596be] font-bold uppercase tracking-widest">
              How it works
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8 space-y-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight">
              Telemetry import flow
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-white/50">
              Walk through the FastF1 → BigQuery pipeline the same way the Colab
              notebook does — cell by cell — with sample shapes at each step.
              No live BigQuery calls; this is a guide.
            </p>
          </div>
          <Link
            href="/admin/jobs"
            className="inline-flex items-center bg-[#2596be] px-4 py-2.5 text-[11px] font-bold uppercase tracking-widest text-white hover:brightness-110"
          >
            Run a real import
          </Link>
        </div>

        {/* Prelude: Cells 0–1 demo config */}
        <section className="border border-white/10 bg-white/[0.02] p-5 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-sm border border-[#2596be]/40 bg-[#2596be]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#2596be]">
              {PIPELINE_PRELUDE.notebookCell}
            </span>
            <h2 className="text-sm font-bold uppercase tracking-widest text-white">
              {PIPELINE_PRELUDE.title}
            </h2>
          </div>
          <p className="text-sm text-white/55">{PIPELINE_PRELUDE.detail}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ConfigChip label="Year(s)" value={demo.years.join(", ")} />
            <ConfigChip label="Race" value={demo.race} />
            <ConfigChip label="Sessions" value={demo.sessions.join(" ")} />
            <ConfigChip
              label="Skip existing"
              value={demo.skipExisting ? "yes" : "no"}
            />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Pipeline steps — click to inspect
          </h2>
          <PipelineFlow
            mode="guide"
            selectedKey={selectedKey}
            onSelect={setSelectedKey}
          />
          {guide && <StepPanel guide={guide} />}
        </section>
      </main>
    </div>
  );
}

function ConfigChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-white/10 px-3 py-2">
      <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-semibold text-white/85">{value}</p>
    </div>
  );
}
