"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CreateJobForm } from "@/components/admin/jobs/CreateJobForm";
import { JobList } from "@/components/admin/jobs/JobList";
import type { JobRow } from "@/lib/jobs/types";

export default function AdminJobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/admin/jobs", { cache: "no-store" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to load jobs");
      setJobs(data.jobs);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 1500);
    return () => clearInterval(id);
  }, [refresh]);

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
              Admin · Jobs
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <Link
              href="/admin"
              className="text-white/50 hover:text-white transition-colors"
            >
              Referral admin
            </Link>
            <span className="text-[#2596be] font-bold uppercase tracking-widest">
              Pipeline jobs
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8 space-y-8">
        <div>
          <h1 className="text-3xl font-black tracking-tight">
            Telemetry import jobs
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-white/50">
            Trigger FastF1 → BigQuery imports (and optional Kaggle upload) from
            here. Status, step progress, and failure logs update live. Privacy
            for v1 is via Vercel Deployment Protection — see ADMIN_JOBS.md.
          </p>
        </div>

        {error && (
          <div className="border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
            <p className="mt-1 text-xs text-red-300/70">
              Ensure DATABASE_URL is set and migrations are applied.
            </p>
          </div>
        )}

        <CreateJobForm
          onCreated={(id) => {
            void refresh();
            router.push(`/admin/jobs/${id}`);
          }}
        />

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-widest text-white/50">
              Recent jobs
            </h2>
            {loading && (
              <span className="text-[11px] text-white/30">Loading…</span>
            )}
          </div>
          <JobList jobs={jobs} />
        </section>
      </main>
    </div>
  );
}
