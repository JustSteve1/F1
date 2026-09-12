"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { PipelineFlow } from "@/components/admin/pipeline/PipelineFlow";
import { StubModeBanner } from "@/components/admin/jobs/WorkerModeBadge";
import type { Fastf1CacheStatus } from "@/lib/jobs/fastf1-cache-types";
import type { WorkerInfo } from "@/lib/jobs/worker-info";
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
  const [cache, setCache] = useState<Fastf1CacheStatus | null>(null);
  const [cacheLoading, setCacheLoading] = useState(false);
  const [stub, setStub] = useState(false);

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

  useEffect(() => {
    if (primaryYear == null || !race) {
      setCache(null);
      setCacheLoading(false);
      return;
    }
    const ac = new AbortController();
    setCacheLoading(true);
    void (async () => {
      try {
        const res = await fetch(
          `/api/admin/import/cache?year=${primaryYear}&race=${encodeURIComponent(race)}`,
          { signal: ac.signal, cache: "no-store" },
        );
        const data = await res.json();
        if (ac.signal.aborted) return;
        if (!res.ok) {
          setCache(null);
          return;
        }
        setCache(data as Fastf1CacheStatus);
      } catch (err) {
        if (ac.signal.aborted) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        setCache(null);
      } finally {
        if (!ac.signal.aborted) setCacheLoading(false);
      }
    })();
    return () => ac.abort();
  }, [primaryYear, race]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/admin/worker", { cache: "no-store" });
        const data = (await res.json()) as WorkerInfo;
        if (!cancelled && res.ok) setStub(!!data.stub);
      } catch {
        if (!cancelled) setStub(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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

  const cacheSessionCodes = useMemo(
    () => new Set(cache?.sessionCodes ?? []),
    [cache],
  );

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
          what exists for the selected event. Cloud Run needs a seeded GCS
          cache; livetiming will not work from a datacenter IP.
        </p>
      </div>

      <StubModeBanner />

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

      {race && primaryYear != null && (
        <CacheBanner
          year={primaryYear}
          race={race}
          cache={cache}
          loading={cacheLoading}
        />
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
                  {cache?.readable &&
                  cache.present &&
                  !cacheSessionCodes.has(session.code) ? (
                    <span className="ml-2 text-[10px] uppercase tracking-widest text-amber-400/90">
                      no GCS
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
      {includeKaggle ? (
        <p className="text-xs text-white/45">
          Kaggle jobs write only{" "}
          <code className="text-white/70">for_kaggle_export</code> (13 CSV
          columns, 2 Hz telemetry JSON) and skip warehouse sessions/laps/telemetry
          and laps_unified.
        </p>
      ) : (
        <p className="text-xs text-white/45">
          Warehouse jobs write sessions, laps, and 10 Hz telemetry. They do not
          update Kaggle.
        </p>
      )}

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
        {submitting ? "Creating…" : stub ? "Create stub run" : "Create & run"}
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

function CacheBanner({
  year,
  race,
  cache,
  loading,
}: {
  year: number;
  race: string;
  cache: Fastf1CacheStatus | null;
  loading: boolean;
}) {
  if (loading && !cache) {
    return (
      <p className="text-xs text-white/40 border border-white/10 px-3 py-2">
        Checking FastF1 GCS cache…
      </p>
    );
  }
  if (!cache) {
    return (
      <p className="text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
        Could not check FastF1 GCS cache for {year} {race}. Cloud Run still
        needs a seeded folder. Use{" "}
        <code className="text-[11px] text-amber-100">
          gcloud storage rsync --recursive ~/.cache/fastf1
          gs://f1-data-library-fastf1-cache/fastf1
        </code>{" "}
        from a home IP (not <code className="text-[11px]">gsutil -m rsync</code>{" "}
        on macOS).
      </p>
    );
  }
  if (!cache.readable) {
    return (
      <p className="text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
        {cache.error || "Could not list FastF1 GCS cache."} Grant{" "}
        <code className="text-[11px] text-amber-100">
          roles/storage.objectViewer
        </code>{" "}
        on the cache bucket to the trigger SA, then refresh. Seed from a
        home/Mac IP with{" "}
        <code className="text-[11px] text-amber-100">
          gcloud storage rsync --recursive ~/.cache/fastf1
          gs://f1-data-library-fastf1-cache/fastf1
        </code>
        . Do not use <code className="text-[11px]">gsutil -m rsync</code> on
        macOS (sys.maxint).
      </p>
    );
  }
  if (!cache.present) {
    const folders = cache.events.map((e) => e.folder).join(", ");
    return (
      <p className="text-sm text-amber-300 border border-amber-500/30 bg-amber-500/10 px-3 py-2">
        No FastF1 GCS cache for {year} {race}
        {folders ? ` (found ${folders})` : ""}. Cloud Run cannot download
        livetiming. Seed on a home/Mac IP, then run{" "}
        <code className="text-[11px] text-amber-100">
          gcloud storage rsync --recursive ~/.cache/fastf1
          gs://f1-data-library-fastf1-cache/fastf1
        </code>
        . Do not use <code className="text-[11px]">gsutil -m rsync</code> on
        macOS (sys.maxint).
      </p>
    );
  }
  const folder = cache.events.map((e) => e.folder).join(", ");
  const codes = cache.sessionCodes.join(", ") || "session folders";
  return (
    <p className="text-xs text-emerald-300/80 border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
      GCS cache: {folder} · {codes}
    </p>
  );
}
