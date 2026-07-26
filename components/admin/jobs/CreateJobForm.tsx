"use client";

import { useState } from "react";
import { SESSION_TYPES, type SessionType } from "@/lib/jobs/steps";

type Props = {
  onCreated: (jobId: string) => void;
};

export function CreateJobForm({ onCreated }: Props) {
  const [years, setYears] = useState(String(new Date().getFullYear()));
  const [race, setRace] = useState("");
  const [sessions, setSessions] = useState<SessionType[]>(["R"]);
  const [noSkip, setNoSkip] = useState(false);
  const [skipQuality, setSkipQuality] = useState(false);
  const [skipUnified, setSkipUnified] = useState(false);
  const [includeKaggle, setIncludeKaggle] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function toggleSession(session: SessionType) {
    setSessions((prev) =>
      prev.includes(session)
        ? prev.filter((s) => s !== session)
        : [...prev, session],
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const yearList = years
        .split(/[,\s]+/)
        .map((y) => Number(y.trim()))
        .filter((y) => Number.isFinite(y));

      const res = await fetch("/api/admin/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          years: yearList,
          race,
          sessions,
          noSkip,
          skipQuality,
          skipUnified,
          includeKaggle,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create job");
      if (data.warning) console.warn(data.warning);
      onCreated(data.job.id);
      setRace("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border border-white/10 bg-white/[0.02] p-5 space-y-5"
    >
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-white">
          Create import job
        </h2>
        <p className="mt-1 text-xs text-white/45">
          FastF1 → BigQuery → optional Kaggle. Progress streams live below.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Year(s)
          </span>
          <input
            value={years}
            onChange={(e) => setYears(e.target.value)}
            placeholder="2025 or 2024 2025"
            className="w-full rounded-sm border border-white/15 bg-black px-3 py-2 text-sm text-white outline-none focus:border-[#2596be]"
            required
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Race name
          </span>
          <input
            value={race}
            onChange={(e) => setRace(e.target.value)}
            placeholder='Australian Grand Prix'
            className="w-full rounded-sm border border-white/15 bg-black px-3 py-2 text-sm text-white outline-none focus:border-[#2596be]"
            required
          />
        </label>
      </div>

      <div className="space-y-2">
        <span className="text-[11px] font-bold uppercase tracking-widest text-white/50">
          Sessions
        </span>
        <div className="flex flex-wrap gap-2">
          {SESSION_TYPES.map((session) => {
            const active = sessions.includes(session);
            return (
              <button
                key={session}
                type="button"
                onClick={() => toggleSession(session)}
                className={`rounded-sm border px-3 py-1.5 text-xs font-bold tracking-wider transition-colors ${
                  active
                    ? "border-[#2596be] bg-[#2596be]/15 text-[#2596be]"
                    : "border-white/15 text-white/50 hover:border-white/30"
                }`}
              >
                {session}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Toggle
          label="No skip (re-import existing)"
          checked={noSkip}
          onChange={setNoSkip}
        />
        <Toggle
          label="Skip quality checks"
          checked={skipQuality}
          onChange={setSkipQuality}
        />
        <Toggle
          label="Skip laps_unified"
          checked={skipUnified}
          onChange={setSkipUnified}
        />
        <Toggle
          label="Include Kaggle upload"
          checked={includeKaggle}
          onChange={setIncludeKaggle}
        />
      </div>

      {error && (
        <p className="text-sm text-red-400 border border-red-500/30 bg-red-500/10 px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting || !sessions.length}
        className="inline-flex items-center justify-center bg-[#2596be] px-5 py-2.5 text-xs font-bold uppercase tracking-widest text-white transition hover:brightness-110 disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create & run"}
      </button>
    </form>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 text-sm text-white/70 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-[#2596be]"
      />
      {label}
    </label>
  );
}
