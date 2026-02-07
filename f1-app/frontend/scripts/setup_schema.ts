
import neo4j from 'neo4j-driver';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const NEO4J_URI = process.env.NEO4J_URI || 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER || 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || 'password';

const driver = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

const SCHEMA_QUERIES = [
    // 1. Season
    "CREATE CONSTRAINT season_year_unique IF NOT EXISTS FOR (s:Season) REQUIRE s.year IS UNIQUE;",
    "CREATE INDEX season_year_idx IF NOT EXISTS FOR (s:Season) ON (s.year);",

    // 2. Circuit
    "CREATE CONSTRAINT circuit_id_unique IF NOT EXISTS FOR (c:Circuit) REQUIRE c.circuit_id IS UNIQUE;",
    "CREATE INDEX circuit_id_idx IF NOT EXISTS FOR (c:Circuit) ON (c.circuit_id);",

    // 3. Event
    "CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE;",
    "CREATE INDEX event_id_idx IF NOT EXISTS FOR (e:Event) ON (e.event_id);",

    // 4. Session
    "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE;",
    "CREATE INDEX session_id_idx IF NOT EXISTS FOR (s:Session) ON (s.session_id);",
    "CREATE INDEX session_date_idx IF NOT EXISTS FOR (s:Session) ON (s.session_date);",

    // 5. Driver
    "CREATE CONSTRAINT driver_id_unique IF NOT EXISTS FOR (d:Driver) REQUIRE d.driver_id IS UNIQUE;",
    "CREATE INDEX driver_id_idx IF NOT EXISTS FOR (d:Driver) ON (d.driver_id);",
    "CREATE INDEX driver_name_idx IF NOT EXISTS FOR (d:Driver) ON (d.full_name);",
    "CREATE INDEX driver_code_idx IF NOT EXISTS FOR (d:Driver) ON (d.code);",

    // 6. Team
    "CREATE CONSTRAINT team_id_unique IF NOT EXISTS FOR (t:Team) REQUIRE t.team_id IS UNIQUE;",
    "CREATE INDEX team_id_idx IF NOT EXISTS FOR (t:Team) ON (t.team_id);",

    // 7. Lap (Composite ID typically, but we'll enforce unique ID)
    "CREATE CONSTRAINT lap_id_unique IF NOT EXISTS FOR (l:Lap) REQUIRE l.lap_id IS UNIQUE;",
    "CREATE INDEX lap_session_idx IF NOT EXISTS FOR (l:Lap) ON (l.session_id);", // Helpful for lookups

    // 8. Audit
    "CREATE CONSTRAINT audit_id_unique IF NOT EXISTS FOR (a:Audit) REQUIRE a.audit_id IS UNIQUE;"
];

async function setupSchema() {
    console.log("🏗️  Applying Graph Schema Constraints...");
    const session = driver.session();

    try {
        for (const query of SCHEMA_QUERIES) {
            console.log(`Executing: ${query}`);
            await session.run(query);
        }
        console.log("✅ Schema setup complete.");
    } catch (e) {
        console.error("❌ Schema setup failed:", e);
    } finally {
        await session.close();
        await driver.close();
    }
}

setupSchema();
