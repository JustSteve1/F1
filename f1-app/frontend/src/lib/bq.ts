
import { BigQuery } from "@google-cloud/bigquery";

// Singleton instance
let bqClient: BigQuery | null = null;

export function getBigQueryClient(): BigQuery {
  if (!bqClient) {
    bqClient = new BigQuery({
      projectId: process.env.BIGQUERY_PROJECT_ID,
      location: process.env.BIGQUERY_LOCATION || "EU",
      // If GOOGLE_APPLICATION_CREDENTIALS is set, it will be automatically used.
    });
  }
  return bqClient;
}
