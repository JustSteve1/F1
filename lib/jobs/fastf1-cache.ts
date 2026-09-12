import { getGoogleAuth } from "./cloud-run";
import type {
  Fastf1CacheEvent,
  Fastf1CacheSession,
  Fastf1CacheStatus,
} from "./fastf1-cache-types";
import {
  cacheFolderMatchesRace,
  sessionCodeFromCacheFolder,
} from "./session-map";
import type { SessionType } from "./steps";

export type {
  Fastf1CacheEvent,
  Fastf1CacheSession,
  Fastf1CacheStatus,
} from "./fastf1-cache-types";

export const DEFAULT_FASTF1_CACHE_URI =
  "gs://f1-data-library-fastf1-cache/fastf1";

const SEED_HINT =
  "Seed from a home/Mac IP (livetiming blocks Cloud Run and Colab), then: gcloud storage rsync --recursive ~/.cache/fastf1 gs://f1-data-library-fastf1-cache/fastf1  — do not use gsutil -m rsync on macOS (sys.maxint).";

export function parseGcsUri(uri: string): { bucket: string; prefix: string } {
  const raw = uri.trim();
  if (!raw.startsWith("gs://")) {
    throw new Error(`FASTF1_CACHE_GCS_URI must start with gs:// (got ${uri})`);
  }
  const without = raw.slice("gs://".length);
  const slash = without.indexOf("/");
  const bucket = slash === -1 ? without : without.slice(0, slash);
  let prefix = slash === -1 ? "" : without.slice(slash + 1);
  if (prefix && !prefix.endsWith("/")) prefix += "/";
  if (!bucket) throw new Error(`Invalid GCS URI: ${uri}`);
  return { bucket, prefix };
}

export function cacheUriFromEnv(): string {
  return (
    process.env.FASTF1_CACHE_GCS_URI?.trim() || DEFAULT_FASTF1_CACHE_URI
  );
}

function lastSegment(prefix: string): string {
  return prefix.replace(/\/+$/, "").split("/").pop() || prefix;
}

type GcsDenied = Error & { status?: number };

async function gcsList(
  token: string,
  bucket: string,
  prefix: string,
  delimiter?: string,
): Promise<{ prefixes: string[]; names: string[] }> {
  const prefixes: string[] = [];
  const names: string[] = [];
  let pageToken: string | undefined;
  do {
    const url = new URL(
      `https://storage.googleapis.com/storage/v1/b/${encodeURIComponent(bucket)}/o`,
    );
    url.searchParams.set("prefix", prefix);
    if (delimiter) url.searchParams.set("delimiter", delimiter);
    url.searchParams.set("maxResults", "1000");
    if (pageToken) url.searchParams.set("pageToken", pageToken);

    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const text = await res.text();
      const err: GcsDenied = new Error(
        `GCS list failed (${res.status}): ${text.slice(0, 300)}`,
      );
      err.status = res.status;
      throw err;
    }
    const data = (await res.json()) as {
      prefixes?: string[];
      items?: { name: string }[];
      nextPageToken?: string;
    };
    prefixes.push(...(data.prefixes ?? []));
    names.push(...(data.items ?? []).map((item) => item.name));
    pageToken = data.nextPageToken;
  } while (pageToken);
  return { prefixes, names };
}

function emptyStatus(
  year: number,
  race: string | null,
  bucket: string,
  prefix: string,
  uri: string,
  extra: Partial<Fastf1CacheStatus>,
): Fastf1CacheStatus {
  return {
    year,
    race,
    bucket,
    prefix,
    uri,
    readable: extra.readable ?? true,
    present: extra.present ?? false,
    events: extra.events ?? [],
    sessionCodes: extra.sessionCodes ?? [],
    missingSessionCodes: extra.missingSessionCodes ?? [],
    error: extra.error ?? null,
    hint: extra.hint ?? SEED_HINT,
  };
}

export async function fetchFastf1Cache(options: {
  year: number;
  race?: string;
  requestedSessions?: SessionType[];
}): Promise<Fastf1CacheStatus> {
  const uri = cacheUriFromEnv();
  const { bucket, prefix } = parseGcsUri(uri);
  const race = options.race?.trim() || null;
  const yearPrefix = `${prefix}${options.year}/`;

  const base = emptyStatus(options.year, race, bucket, prefix, uri, {});

  let token: string;
  try {
    const auth = getGoogleAuth();
    const client = await auth.getClient();
    const access = await client.getAccessToken();
    if (!access.token) {
      return emptyStatus(options.year, race, bucket, prefix, uri, {
        readable: false,
        error: "No GCP access token to list FastF1 cache",
      });
    }
    token = access.token;
  } catch (err) {
    return emptyStatus(options.year, race, bucket, prefix, uri, {
      readable: false,
      error: err instanceof Error ? err.message : "Failed to auth for GCS",
    });
  }

  try {
    const yearList = await gcsList(token, bucket, yearPrefix, "/");
    let eventPrefixes = yearList.prefixes;
    if (race) {
      eventPrefixes = eventPrefixes.filter((p) =>
        cacheFolderMatchesRace(lastSegment(p), race),
      );
    }

    const events: Fastf1CacheEvent[] = [];
    for (const eventPrefix of eventPrefixes) {
      const sessionList = await gcsList(token, bucket, eventPrefix, "/");
      const sessions: Fastf1CacheSession[] = sessionList.prefixes.map(
        (sessionPrefix) => {
          const folder = lastSegment(sessionPrefix);
          return { folder, code: sessionCodeFromCacheFolder(folder) };
        },
      );
      events.push({
        folder: lastSegment(eventPrefix),
        uri: `gs://${bucket}/${eventPrefix.replace(/\/+$/, "")}`,
        sessions,
      });
    }

    const sessionCodes = [
      ...new Set(
        events.flatMap((ev) =>
          ev.sessions.map((s) => s.code).filter((c): c is string => !!c),
        ),
      ),
    ];
    const missingSessionCodes = (options.requestedSessions ?? []).filter(
      (code) => !sessionCodes.includes(code),
    );

    return {
      ...base,
      readable: true,
      present: events.length > 0,
      events,
      sessionCodes,
      missingSessionCodes,
      error: null,
      hint: events.length
        ? SEED_HINT
        : `No FastF1 cache folder for ${options.year}${race ? ` ${race}` : ""}. ${SEED_HINT}`,
    };
  } catch (err) {
    const status = (err as GcsDenied).status;
    const message = err instanceof Error ? err.message : "GCS list failed";
    const denied = status === 401 || status === 403;
    return emptyStatus(options.year, race, bucket, prefix, uri, {
      readable: false,
      error: denied
        ? `${message} Grant roles/storage.objectViewer on gs://${bucket} to the trigger SA.`
        : message,
    });
  }
}
