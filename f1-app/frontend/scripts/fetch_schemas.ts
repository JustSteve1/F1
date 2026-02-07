
import { BigQuery } from "@google-cloud/bigquery";
import fs from "fs";

const BQ_PROJECT = process.env.NEXT_PUBLIC_BQ_PROJECT_ID || 'f1-data-library';
const BQ_DATASET = process.env.NEXT_PUBLIC_BQ_DATASET_ID || 'f1_data_library_DS';
const TABLES = [
    "laps_clean",
    "public_circuits",
    "public_drivers",
    "public_laps",
    "public_races",
    "public_seasons",
    "public_session_data_audit",
    "public_sessions"
];

const bq = new BigQuery({ projectId: BQ_PROJECT, location: 'EU' });

async function fetchSchemas() {
    console.log("Fetching table schemas...");
    const schemaOut: any = {
        project: BQ_PROJECT,
        dataset: BQ_DATASET,
        location: "EU",
        allowlist: TABLES,
        tables: {}
    };

    for (const tableId of TABLES) {
        try {
            const [metadata] = await bq.dataset(BQ_DATASET).table(tableId).getMetadata();
            const schema = metadata.schema;
            const columns = schema.fields.map((f: any) => f.name);

            schemaOut.tables[tableId] = {
                columns: columns,
                description: `Imported from BigQuery table ${tableId}`
            };
            console.log(`✅ Fetched ${tableId}`);
        } catch (e: any) {
            console.error(`❌ Failed ${tableId}: ${e.message}`);
        }
    }

    fs.writeFileSync("src/app/pitwall/skills/schema.sandbox.json", JSON.stringify(schemaOut, null, 4));
    console.log("Written to src/app/pitwall/skills/schema.sandbox.json");
}

fetchSchemas();
