
import { BigQuery } from "@google-cloud/bigquery";

async function listTables() {
    const bq = new BigQuery({
        projectId: process.env.BIGQUERY_PROJECT_ID,
        location: process.env.BIGQUERY_LOCATION || "EU",
    });

    const datasetId = "f1_data_library_DS";

    try {
        const [tables] = await bq.dataset(datasetId).getTables();
        console.log("Tables:");
        for (const table of tables) {
            console.log(`- ${table.id}`);
            const [metadata] = await table.getMetadata();
            const schema = metadata.schema;
            if (schema && schema.fields) {
                console.log(`  Columns: ${schema.fields.map((f: any) => f.name).join(", ")}`);
            }
        }
    } catch (error) {
        console.error("Error listing tables:", error);
    }
}

listTables();
