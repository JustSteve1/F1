import { Pool, type QueryResultRow } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __intervalPgPool: Pool | undefined;
}

function createPool() {
  const raw = process.env.DATABASE_URL;
  if (!raw) {
    throw new Error("DATABASE_URL is not set");
  }

  const isLocal = raw.includes("localhost") || raw.includes("127.0.0.1");
  // pg-connection-string v2 treats sslmode=require as verify-full. For Cloud SQL
  // without a server CA bundle, force libpq-compatible require + disable CA check.
  let connectionString = raw;
  try {
    const url = new URL(raw);
    if (!isLocal) {
      url.searchParams.set("uselibpqcompat", "true");
      if (!url.searchParams.get("sslmode")) {
        url.searchParams.set("sslmode", "require");
      }
      connectionString = url.toString();
    }
  } catch {
    // keep raw connection string
  }

  const ssl =
    isLocal && process.env.DATABASE_SSL !== "true"
      ? undefined
      : { rejectUnauthorized: false };

  return new Pool({
    connectionString,
    ssl,
    max: 5,
  });
}

export function getPool(): Pool {
  if (!global.__intervalPgPool) {
    global.__intervalPgPool = createPool();
  }
  return global.__intervalPgPool;
}

export async function query<T extends QueryResultRow = QueryResultRow>(
  text: string,
  params?: unknown[],
) {
  return getPool().query<T>(text, params);
}
