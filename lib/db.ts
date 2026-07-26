import { Pool, type QueryResultRow } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __intervalPgPool: Pool | undefined;
}

function createPool() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is not set");
  }

  return new Pool({
    connectionString,
    ssl:
      process.env.DATABASE_SSL === "false"
        ? undefined
        : connectionString.includes("localhost") ||
            connectionString.includes("127.0.0.1")
          ? undefined
          : { rejectUnauthorized: false },
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
