import { BigQuery } from "@google-cloud/bigquery";
import type { SessionType } from "./steps";

function getBigQuery(): BigQuery {
  const projectId =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const keyJson = process.env.GOOGLE_SERVICE_ACCOUNT_KEY;
  if (keyJson) {
    return new BigQuery({ projectId, credentials: JSON.parse(keyJson) });
  }
  const keyFile = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (keyFile) {
    return new BigQuery({ projectId, keyFilename: keyFile });
  }
  return new BigQuery({ projectId });
}

export type ImportStatusResult = {
  year: number;
  race: string;
  sessionsInBigQuery: SessionType[];
  missingFromRequest: SessionType[];
  telemetryRows: number;
  lapsRows: number;
};

export async function fetchImportStatus(
  year: number,
  race: string,
  requestedSessions?: SessionType[],
): Promise<ImportStatusResult> {
  const project =
    process.env.BQ_PROJECT || process.env.GCP_PROJECT_ID || "f1-data-library";
  const dataset = process.env.BQ_DATASET || "f1_data_library_DS";
  const bq = getBigQuery();

  const sessionsSql = `
    SELECT DISTINCT session_type
    FROM \`${project}.${dataset}.telemetry\`
    WHERE season = @year
      AND event_name = @race
    ORDER BY session_type
  `;

  const countsSql = `
    SELECT
      (SELECT COUNT(*) FROM \`${project}.${dataset}.telemetry\`
       WHERE season = @year AND event_name = @race) AS telemetry_rows,
      (SELECT COUNT(*) FROM \`${project}.${dataset}.laps\`
       WHERE season = @year AND event_name = @race) AS laps_rows
  `;

  const [[sessionRows], [countRows]] = await Promise.all([
    bq.query({
      query: sessionsSql,
      params: { year, race },
      types: { year: "INT64", race: "STRING" },
    }),
    bq.query({
      query: countsSql,
      params: { year, race },
      types: { year: "INT64", race: "STRING" },
    }),
  ]);

  const sessionsInBigQuery = (sessionRows as Array<{ session_type: string }>).map(
    (row) => row.session_type as SessionType,
  );

  const missingFromRequest = requestedSessions
    ? requestedSessions.filter((s) => !sessionsInBigQuery.includes(s))
    : [];

  const counts = countRows[0] as {
    telemetry_rows: number | string;
    laps_rows: number | string;
  };

  return {
    year,
    race,
    sessionsInBigQuery,
    missingFromRequest,
    telemetryRows: Number(counts?.telemetry_rows ?? 0),
    lapsRows: Number(counts?.laps_rows ?? 0),
  };
}
