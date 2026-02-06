
import { BigQuery } from "@google-cloud/bigquery";
import neo4j from 'neo4j-driver';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

// Config
const BQ_PROJECT = process.env.NEXT_PUBLIC_BQ_PROJECT_ID || 'f1-data-library';
const BQ_DATASET = process.env.NEXT_PUBLIC_BQ_DATASET_ID || 'f1_data_library_DS';
const NEO4J_URI = process.env.NEO4J_URI || 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER || 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || 'password';

const bq = new BigQuery({ projectId: BQ_PROJECT, location: 'EU' });
const driver = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

async function seed() {
    console.log("🌱 Seeding Knowledge Graph...");
    const session = driver.session();

    try {
        // 1. Seed Drivers
        console.log("Fetching Drivers from BigQuery...");
        const [driverRows] = await bq.query({
            query: `SELECT driver_id, driver_code, full_name, nationality 
                    FROM \`${BQ_DATASET}.public_drivers\``
        });

        console.log(`Syncing ${driverRows.length} drivers...`);
        for (const row of driverRows) {
            await session.run(`
                MERGE (d:Driver {driver_id: $driver_id})
                SET d.code = $code, d.name = $name, d.nationality = $nationality
            `, {
                driver_id: row.driver_id,
                code: row.driver_code,
                name: row.full_name,
                nationality: row.nationality
            });
        }

        // 2. Seed Sessions (Inferred from Laps)
        console.log("Inferring Sessions from Laps...");
        // This is expensive but necessary without a sessions table. 
        // Grouping by session_id to get distinct sessions.
        const [sessionRows] = await bq.query({
            query: `
                SELECT 
                    session_id, 
                    ANY_VALUE(session_type) as session_type,
                    COUNT(DISTINCT driver_id) as driver_count
                FROM \`${BQ_DATASET}.laps_clean\`
                GROUP BY session_id
                LIMIT 100 
            ` // Limit for v1 safety
        });

        console.log(`Syncing ${sessionRows.length} sessions...`);
        for (const row of sessionRows) {
            await session.run(`
                MERGE (s:Session {session_id: $session_id})
                SET s.type = $type, s.driver_count = $count
            `, {
                session_id: row.session_id.toString(),
                type: row.session_type,
                count: row.driver_count
            });
        }

        // 3. Link Drivers to Sessions
        console.log("Linking Drivers -> Sessions...");
        // Again, using laps to find who drove where
        const [linkRows] = await bq.query({
            query: `
                SELECT DISTINCT session_id, driver_id
                FROM \`${BQ_DATASET}.laps_clean\`
                LIMIT 1000
            `
        });

        for (const row of linkRows) {
            await session.run(`
                MATCH (d:Driver {driver_id: $driver_id})
                MATCH (s:Session {session_id: $session_id})
                MERGE (d)-[:DROVE_IN]->(s)
            `, {
                driver_id: row.driver_id,
                session_id: row.session_id.toString()
            });
        }

        console.log("✅ Seeding Complete.");

    } catch (e) {
        console.error("Error seeding:", e);
    } finally {
        await session.close();
        await driver.close();
    }
}

seed();
