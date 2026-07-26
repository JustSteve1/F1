"use client";

import Link from "next/link";
import { StatusBadge } from "./StatusBadge";
import type { JobRow } from "@/lib/jobs/types";

export function JobList({
  jobs,
  selectedId,
}: {
  jobs: JobRow[];
  selectedId?: string;
}) {
  if (!jobs.length) {
    return (
      <div className="border border-dashed border-white/15 px-4 py-10 text-center text-sm text-white/40">
        No jobs yet. Create one to start an import.
      </div>
    );
  }

  return (
    <div className="border border-white/10 divide-y divide-white/10">
      {jobs.map((job) => {
        const active = job.id === selectedId;
        const years = job.params?.years?.join(", ") ?? "—";
        return (
          <Link
            key={job.id}
            href={`/admin/jobs/${job.id}`}
            className={`block px-4 py-3 transition-colors hover:bg-white/[0.03] ${
              active ? "bg-[#2596be]/10" : ""
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  {job.params?.race || "Untitled race"}
                </p>
                <p className="mt-0.5 text-xs text-white/40">
                  {years} · {(job.params?.sessions || []).join(" ")} ·{" "}
                  {new Date(job.created_at).toLocaleString()}
                </p>
              </div>
              <StatusBadge status={job.status} />
            </div>
            <div className="mt-2 h-1 w-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-[#2596be] transition-all duration-500"
                style={{ width: `${Math.min(100, job.progress_pct)}%` }}
              />
            </div>
            <p className="mt-1.5 truncate text-[11px] text-white/45">
              {job.status_message || job.current_step || "—"}
            </p>
          </Link>
        );
      })}
    </div>
  );
}
