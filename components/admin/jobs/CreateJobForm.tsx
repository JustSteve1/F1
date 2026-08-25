"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PipelineFlow } from "@/components/admin/pipeline/PipelineFlow";
import type { SessionType } from "@/lib/jobs/steps";
import type { CatalogEvent, ImportCatalog } from "@/lib/jobs/session-map";

type Props = {
  onCreated: (jobId: string) => void;
};

export function CreateJobForm({ onCreated }: Props) {
  const [years, setYears] = useState(String(new Date().getFullYear()));
  const [catalogYear, setCatalogYear] = useState<number | null>(null);
  const [catalog, setCatalog] = useState<ImportCatalog | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const [race, setRace] = useState("");
  const [sessions, setSessions] = useState<SessionType[]>([]);
  const [noSkip, setNoSkip] = useState(false);
  const [skipQuality, setSkipQuality] = useState(false);
  const [skipUnified, setSkipUnified] = useState(false);
  const [includeKaggle, setIncludeKaggle] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const primaryYear = useMemo(() => {
    const first = years
      .split(/[,\s]+/)
      .map((y) => Number(y.trim()))
      .find((y) => Number.isFinite(y));
    return first ?? null;
  }, [years]);

  const selectedEvent: CatalogEvent | null = useMemo(() => {
    if (!catalog || !race) return null;
    return (
      catalog.events.find(
        (e) => e.eventName.toLowerCase() === race.toLowerCase(),
      ) ?? null
    );
  }, [catalog, race]);

  const loadCatalog = useCallback(async (year: number) => {
    setCatalogLoading(true);
    setCatalogError("");
    try {
      const res = await fetch(`/api/admin/import-catalog?year=${year}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to load schedule");
      setCatalog(data as ImportCatalog);
      setCatalogYear(year);
      setRace((prev) => {
        const stillValid = (data as ImportCatalog).events.some(
          (e) => e.eventName === prev,
        );
        return stillValid ? prev : "";
      });
      setSessions([]);
    } catch (err) {
      setCatalog(null);
      setCatalogYear(null);
      setCatalogError(
        err instanceof Error ? err.message : "Failed to load schedule",
      );
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    if (primaryYear == null) return;
    if (catalogYear === primaryYear && catalog) return;
    void loadCatalog(primaryYear);
  }, [primaryYear, catalogYear, catalog, loadCatalog]);

  const eventSessionKey = selectedEvent
    ? `${selectedEvent.eventName}:${selectedEvent.sessions.map((s) => s.code).join(",")}`
    : "";

  useEffect(() => {
    if (!selectedEvent) {
      setSessions([]);
      return;
    }
    const allowed = new Set(selectedEvent.sessions.map((s) => s.code));
    setSessions((prev) => prev.filter((s) => allowed.has(s)));
    // Only re-filter when the race's available session codes change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventSessionKey]);

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

      if (!race) throw new Error("Select a race from the schedule");
      if (!sessions.length) throw new Error("Select at least one session");

      const sessionLabels: Record<string, string> = {};
      for (const s of selectedEvent?.sessions ?? []) {
        if (sessions.includes(s.code as SessionType)) {
          sessionLabels[s.code] = s.label;
        }
      }

      const res = await fetch("/api/admin/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          years: yearList,
          race,
          sessions,
          sessionLabels,
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
      setSessions([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit =
    !submitting &&
    !catalogLoading &&
    !!selectedEvent &&
    sessions.length > 0 &&
    primaryYear != null;

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
          FastF1 schedule → BigQuery → optional Kaggle. Sessions are limited to
          what exists for the selected event.
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
            onBlur={() => {
              if (primaryYear != null) void loadCatalog(primaryYear);
            }}
            placeholder="2026 or 2025 2026"
            className="w-full rounded-sm border border-white/15 bg-black px-3 py-2 text-sm text-white outline-none focus:border-[#2596be]"
            required
          />
          <span className="block text-[10px] text-white/35">
            Schedule loads for the first year listed.
          </span>
        </label>

        <label className="block space-y-1.5">
          <span className="text-[11px] font-bold uppercase tracking-widest text-white/50">
            Race
          </span>
          <select
            value={race}
            onChange={(e) => setRace(e.target.value)}
            disabled={!catalog?.events.length || catalogLoading}
            className="w-full rounded-sm border border-white/15 bg-black px-3 py-2 text-sm text-white outline-none focus:border-[#2596be] disabled:opacity-50"
            required
          >
            <option value="">
              {catalogLoading
                ? "Loading schedule…"
                : catalog?.events.length
                  ? "Select race…"
                  : "No events loaded"}
            </option>
            {(catalog?.events ?? []).map((ev) => (
              <option key={ev.eventName} value={ev.eventName}>
                {ev.round != null ? `R${ev.round} · ` : ""}
                {ev.eventName}
              </option>
            ))}
          </select>
          {selectedEvent && (
            <span className="block text-[10px] text-white/35">
              {selectedEvent.eventFormat || "format unknown"}
              {selectedEvent.location ? ` · ${selectedEvent.location}` : ""}
            </span>
          )}
        </label>
      </div>

      {catalogError && (
        <p className="text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
          {catalogError}
        </p>
      )}

      <div className="space-y-2">
        <span className="text-[11px] font-bold uppercase tracking-widest text-white/50">
          Sessions
        </span>
        {!selectedEvent ? (
          <p className="text-xs text-white/40">Select a race to see sessions.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selectedEvent.sessions.map((session) => {
              const code = session.code as SessionType;
              const active = sessions.includes(code);
              return (
                <button
                  key={session.code}
                  type="button"
                  onClick={() => toggleSession(code)}
                  className={`rounded-sm border px-3 py-1.5 text-xs font-bold tracking-wider transition-colors ${
                    active
                      ? "border-[#2596be] bg-[#2596be]/15 text-[#2596be]"
                      : "border-white/15 text-white/50 hover:border-white/30"
                  }`}
                >
                  <span>
                    {session.code} · {session.label}
                  </span>
                  {session.inBigQuery ? (
                    <span
                      className={`ml-2 text-[10px] uppercase tracking-widest ${
                        active ? "text-[#2596be]/80" : "text-emerald-400/80"
                      }`}
                    >
                      in BQ
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Toggle
          label="No skip (replace session in BQ)"
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

      <div className="space-y-2 border border-white/10 px-3 py-3">
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/40">
          Steps that will run
        </p>
        <PipelineFlow
          mode="preview"
          includeBookends
          params={{
            skipQuality,
            skipUnified,
            includeKaggle,
            years: primaryYear != null ? [primaryYear] : [2025],
            race: race || "—",
            sessions,
            noSkip,
          }}
        />
      </div>

      {error && (
        <p className="text-sm text-red-400 border border-red-500/30 bg-red-500/10 px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
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
