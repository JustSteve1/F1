"use client";

import { useEffect, useState } from "react";
import type { WorkerInfo } from "@/lib/jobs/worker-info";

export function WorkerModeBadge() {
  const [info, setInfo] = useState<WorkerInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/admin/worker", { cache: "no-store" });
        const data = (await res.json()) as WorkerInfo;
        if (!cancelled && res.ok) setInfo(data);
      } catch {
        if (!cancelled) setInfo(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!info) return null;

  if (info.stub) {
    return (
      <span
        title="JOB_WORKER_MODE=stub — jobs simulate progress and do not write BigQuery"
        className="inline-flex items-center rounded-sm border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-amber-300"
      >
        Stub
      </span>
    );
  }

  if (info.mode === "local") {
    return (
      <span
        title="JOB_WORKER_MODE=local — Python worker on this machine"
        className="inline-flex items-center rounded-sm border border-sky-400/40 bg-sky-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-sky-300"
      >
        Local worker
      </span>
    );
  }

  const ingestLabel = info.ingestOk ? "FastF1" : info.ingestSource;
  return (
    <span
      title={`${info.jobName} · ${info.region} · INGEST_SOURCE=${info.ingestSource}`}
      className={`inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
        info.ingestOk
          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
          : "border-red-500/50 bg-red-500/10 text-red-300"
      }`}
    >
      Cloud Run · {ingestLabel}
    </span>
  );
}

export function StubModeBanner() {
  const [stub, setStub] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/admin/worker", { cache: "no-store" });
        const data = (await res.json()) as WorkerInfo;
        if (!cancelled && res.ok) setStub(data.stub);
      } catch {
        if (!cancelled) setStub(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!stub) return null;

  return (
    <p className="text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
      <span className="font-bold uppercase tracking-widest text-[10px]">
        Stub worker
      </span>
      <span className="block mt-1">
        This deploy has <code className="text-[11px] text-amber-100">JOB_WORKER_MODE=stub</code>.
        Create &amp; run will animate steps only — it will not load FastF1 or
        write BigQuery. Set <code className="text-[11px] text-amber-100">JOB_WORKER_MODE=cloud_run</code>{" "}
        on Vercel Preview and Production.
      </span>
    </p>
  );
}
