/** FastF1 schedule session display name → worker short code. */
export const SESSION_NAME_TO_CODE: Record<string, string> = {
  "practice 1": "FP1",
  "practice 2": "FP2",
  "practice 3": "FP3",
  qualifying: "Q",
  "sprint qualifying": "SQ",
  "sprint shootout": "SQ",
  sprint: "S",
  race: "R",
};

export function sessionCodeFromLabel(label: string | null | undefined): string | null {
  if (!label) return null;
  const key = label.trim().toLowerCase();
  if (!key) return null;
  return SESSION_NAME_TO_CODE[key] ?? null;
}

/** FastF1 / GCS folder token for an event name, e.g. "Dutch Grand Prix" → "Dutch_Grand_Prix". */
export function raceToken(race: string): string {
  return race.trim().replace(/\s+/g, "_");
}

export function cacheFolderMatchesRace(folder: string, race: string): boolean {
  const token = raceToken(race).toLowerCase();
  if (!token) return false;
  return folder.toLowerCase().includes(token);
}

/** Map a cache session folder like `2026-08-23_Practice_1` to FP1/Q/R/…. */
export function sessionCodeFromCacheFolder(
  folder: string,
): string | null {
  const name = folder.replace(/\/+$/, "").split("/").pop() ?? "";
  const label = name.replace(/^\d{4}-\d{2}-\d{2}_/, "").replace(/_/g, " ");
  return sessionCodeFromLabel(label);
}

export type CatalogSession = {
  code: string;
  label: string;
  dateUtc: string | null;
  inBigQuery?: boolean;
};

export type CatalogEvent = {
  eventName: string;
  round: number | null;
  eventFormat: string | null;
  location: string | null;
  country?: string | null;
  sessions: CatalogSession[];
};

export type ImportCatalog = {
  year: number;
  events: CatalogEvent[];
};
