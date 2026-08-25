"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { JobDetail } from "@/components/admin/jobs/JobDetail";
import { JobList } from "@/components/admin/jobs/JobList";
import { WorkerModeBadge } from "@/components/admin/jobs/WorkerModeBadge";
import type { JobDetail as JobDetailType, JobRow } from "@/lib/jobs/types";

export default function AdminJobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [job, setJob] = useState<JobDetailType | null>(null);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [detailRes, listRes] = await Promise.all([
        fetch(`/api/admin/jobs/${id}`, { cache: "no-store" }),
        fetch("/api/admin/jobs", { cache: "no-store" }),
      ]);
      const detailData = await detailRes.json();
      const listData = await listRes.json();
      if (!detailRes.ok) throw new Error(detailData.error || "Job not found");
      setJob(detailData.job);
      if (listRes.ok) setJobs(listData.jobs);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load job");
    }
  }, [id]);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 1500);
    return () => clearInterval(timer);
  }, [refresh]);

  async function handleCancel() {
    setBusy(true);
    try {
      const res = await fetch(`/api/admin/jobs/${id}/cancel`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Cancel failed");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleRetry() {
    setBusy(true);
    try {
      const res = await fetch(`/api/admin/jobs/${id}/retry`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Retry failed");
      router.push(`/admin/jobs/${data.job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
      setBusy(false);
    }
  }

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
              Admin · Job detail
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <WorkerModeBadge />
            <Link
              href="/admin/pipeline"
              className="text-white/50 hover:text-white transition-colors"
            >
              How the pipeline works
            </Link>
            <Link
              href="/admin/jobs"
              className="text-white/50 hover:text-white transition-colors"
            >
              ← All jobs
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {error && (
          <div className="mb-6 border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <aside className="space-y-3">
            <h2 className="text-[11px] font-bold uppercase tracking-widest text-white/40">
              Jobs
            </h2>
            <JobList jobs={jobs} selectedId={id} />
          </aside>

          <section>
            {!job ? (
              <div className="border border-white/10 px-4 py-12 text-center text-sm text-white/40">
                Loading job…
              </div>
            ) : (
              <JobDetail
                job={job}
                onCancel={handleCancel}
                onRetry={handleRetry}
                busy={busy}
              />
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
