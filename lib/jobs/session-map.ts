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
