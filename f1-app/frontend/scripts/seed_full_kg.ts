
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

// Target Years
const YEARS = [2024, 2025];
// Batch size for Laps
const BATCH_SIZE = 5000;

const bq = new BigQuery({ projectId: BQ_PROJECT, location: 'EU' });
const driver = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

async function runCypher(session: any, query: string, params: any = {}) {
    try {
        await session.run(query, params);
    } catch (e: any) {
        console.error(`Cypher Error: ${e.message}`, query);
        throw e;
    }
}

async function seedFull() {
    console.log(`🌍 Starting Full Seed for Years: ${YEARS.join(', ')}`);
    const session = driver.session();

    try {
        // =================================================================================================
        // 1. Reference Data (Drivers, Circuits, Seasons)
        // =================================================================================================
        console.log("--- Syncing Reference Data ---");

        // Seasons
        console.log(" > Seasons");
        const [seasons] = await bq.query({ query: `SELECT * FROM \`${BQ_DATASET}.public_seasons\` WHERE year IN (${YEARS.join(',')})` });
        for (const row of seasons) {
            await runCypher(session, `
                MERGE (s:Season {year: $year})
                SET s.season_id = $id
            `, { year: row.year, id: row.season_id });
        }

        // Circuits (All, as they don't change much)
        console.log(" > Circuits");
        const [circuits] = await bq.query({ query: `SELECT * FROM \`${BQ_DATASET}.public_circuits\`` });
        for (const row of circuits) {
            await runCypher(session, `
                MERGE (c:Circuit {circuit_id: $id})
                SET c.name = $name, c.country = $country
            `, { id: row.circuit_id, name: row.name, country: row.country });
        }

        // Drivers (All)
        console.log(" > Drivers");
        const [drivers] = await bq.query({ query: `SELECT * FROM \`${BQ_DATASET}.public_drivers\`` });
        for (const row of drivers) {
            await runCypher(session, `
                MERGE (d:Driver {driver_id: $id})
                SET d.code = $code, d.full_name = $full_name, d.nationality = $nat
            `, { id: row.driver_id, code: row.driver_code, full_name: row.full_name, nat: row.nationality });
        }

        // =================================================================================================
        // 2. Event Hierarchy (Event -> Session)
        // =================================================================================================
        console.log("--- Syncing Event Hierarchy ---");

        // Races (Events) linked to Seasons and Circuits
        // Filter by year via join to seasons if needed, or assuming race_date/season_id
        console.log(" > Events (Races)");
        const [races] = await bq.query({
            query: `
                SELECT r.*, s.year 
                FROM \`${BQ_DATASET}.public_races\` r
                JOIN \`${BQ_DATASET}.public_seasons\` s ON r.season_id = s.season_id
                WHERE s.year IN (${YEARS.join(',')})
            `
        });

        for (const row of races) {
            const raceDateStr = row.race_date.value || row.race_date; // Handle BQ Date object
            await runCypher(session, `
                MATCH (s:Season {year: $year})
                MATCH (c:Circuit {circuit_id: $circuit_id})
                MERGE (e:Event {event_id: $id})
                SET e.name = $name, e.date = date($date)
                MERGE (s)-[:HAS_EVENT]->(e)
                MERGE (e)-[:HELD_AT]->(c)
            `, {
                year: row.year,
                circuit_id: row.circuit_id,
                id: row.race_id,
                name: row.race_name,
                date: raceDateStr
            });
        }

        // Sessions
        console.log(" > Sessions");
        // We need race_id to link, and filtered by the races we just inserted
        const [sessionsBQ] = await bq.query({
            query: `
                SELECT sess.* 
                FROM \`${BQ_DATASET}.public_sessions\` sess
                JOIN \`${BQ_DATASET}.public_races\` r ON sess.race_id = r.race_id
                JOIN \`${BQ_DATASET}.public_seasons\` s ON r.season_id = s.season_id
                WHERE s.year IN (${YEARS.join(',')})
            `
        });

        for (const row of sessionsBQ) {
            const sessDateStr = row.session_date.value || row.session_date; // Handle BQ Datetime
            await runCypher(session, `
                MATCH (e:Event {event_id: $race_id})
                MERGE (s:Session {session_id: $id})
                SET s.type = $type, s.date = datetime($date)
                MERGE (e)-[:HAS_SESSION]->(s)
            `, {
                race_id: row.race_id,
                id: row.session_id,
                type: row.session_type,
                date: sessDateStr
            });
        }

        // =================================================================================================
        // 3. Teams (Inferred)
        // =================================================================================================
        console.log("--- Inferring Teams ---");
        // Get distinct teams from public_laps for the target years
        const [teams] = await bq.query({
            query: `
                SELECT DISTINCT team_id 
                FROM \`${BQ_DATASET}.public_laps\` l
                JOIN \`${BQ_DATASET}.public_sessions\` s ON l.session_id = s.session_id
                JOIN \`${BQ_DATASET}.public_races\` r ON s.race_id = r.race_id
                JOIN \`${BQ_DATASET}.public_seasons\` sea ON r.season_id = sea.season_id
                WHERE sea.year IN (${YEARS.join(',')}) AND team_id IS NOT NULL
            `
        });

        for (const row of teams) {
            await runCypher(session, `
                MERGE (t:Team {team_id: $id})
            `, { id: row.team_id });
        }

        // =================================================================================================
        // 4. Laps & Participation (The Heavy Lift)
        // =================================================================================================
        console.log(`--- Syncing Laps & Participation (Batch Size: ${BATCH_SIZE}) ---`);

        // We select key columns to link nodes
        // Creating relationships: Driver->Session, Driver->Lap, Session->Lap, Driver->Team
        // Note: Laps table in BQ -> public_laps

        // We process by Session to keep it manageable? No, let's stream by OFFSET.
        // First get total count
        const [countRow] = await bq.query({
            query: `
                SELECT COUNT(*) as count
                FROM \`${BQ_DATASET}.public_laps\` l
                JOIN \`${BQ_DATASET}.public_sessions\` s ON l.session_id = s.session_id
                JOIN \`${BQ_DATASET}.public_races\` r ON s.race_id = r.race_id
                JOIN \`${BQ_DATASET}.public_seasons\` sea ON r.season_id = sea.season_id
                WHERE sea.year IN (${YEARS.join(',')})
            `
        });
        const totalLaps = countRow[0].count;
        console.log(`Total Laps to sync: ${totalLaps}`);

        let processed = 0;

        while (processed < totalLaps) {
            const [laps] = await bq.query({
                query: `
                    SELECT 
                        l.lap_id, l.session_id, l.driver_id, l.team_id,
                        l.lap_number, l.lap_time_ms, l.sector1_ms, l.sector2_ms, l.sector3_ms,
                        l.compound, l.position
                    FROM \`${BQ_DATASET}.public_laps\` l
                    JOIN \`${BQ_DATASET}.public_sessions\` s ON l.session_id = s.session_id
                    JOIN \`${BQ_DATASET}.public_races\` r ON s.race_id = r.race_id
                    JOIN \`${BQ_DATASET}.public_seasons\` sea ON r.season_id = sea.season_id
                    WHERE sea.year IN (${YEARS.join(',')})
                    ORDER BY l.session_id, l.driver_id, l.lap_number
                    LIMIT ${BATCH_SIZE} OFFSET ${processed}
                `
            });

            if (laps.length === 0) break;

            // Batch Transaction
            const txc = session.beginTransaction();
            try {
                for (const row of laps) {
                    await txc.run(`
                        MATCH (s:Session {session_id: $session_id})
                        MATCH (d:Driver {driver_id: $driver_id})
                        
                        // Create Lap
                        MERGE (l:Lap {lap_id: $lap_id})
                        SET l.number = $lap_num, l.time = $time, l.pos = $pos, l.compound = $comp
                        
                        // Links
                        MERGE (s)-[:CONTAINS_LAP]->(l)
                        MERGE (d)-[:COMPLETED_LAP]->(l)
                        MERGE (d)-[:PARTICIPATED_IN]->(s)
                        
                        // Team Link (if team_id present)
                        WITH d, l, $team_id as tid
                        CALL {
                            WITH d, tid
                            MATCH (t:Team {team_id: tid})
                            MERGE (d)-[:DRIVES_FOR]->(t)
                        }
                    `, {
                        session_id: row.session_id, // ensure string vs int match
                        driver_id: row.driver_id,
                        lap_id: row.lap_id || `${row.session_id}_${row.driver_id}_${row.lap_number}`, // Fallback ID construction
                        lap_num: row.lap_number,
                        time: row.lap_time_ms,
                        pos: row.position,
                        comp: row.compound,
                        team_id: row.team_id
                    });
                }
                await txc.commit();
                processed += laps.length;
                console.log(` > Processed ${processed} / ${totalLaps}`);
            } catch (err) {
                console.error("Batch failed, rolling back", err);
                await txc.rollback();
                throw err;
            }
        }

        console.log("✅ Full Seed Complete.");

    } catch (e) {
        console.error("❌ Seed Failed:", e);
    } finally {
        await session.close();
        await driver.close();
    }
}

seedFull();
