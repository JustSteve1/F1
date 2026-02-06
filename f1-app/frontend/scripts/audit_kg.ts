
import neo4j from 'neo4j-driver';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const NEO4J_URI = process.env.NEO4J_URI || 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER || 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || 'password';

const driver = neo4j.driver(NEO4J_URI, neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD));

async function audit() {
    console.log("🔍 Auditing Knowledge Graph...");
    const session = driver.session();

    try {
        const result = await session.run(`
            CALL {
                MATCH (d:Driver) RETURN count(d) as drivers
            }
            CALL {
                MATCH (s:Session) RETURN count(s) as sessions
            }
            CALL {
                MATCH ()-[r:DROVE_IN]->() RETURN count(r) as relationships
            }
            CALL {
                MATCH (l:Lap) RETURN count(l) as laps
            }
            RETURN drivers, sessions, relationships, laps
        `);

        const record = result.records[0];
        console.log(`- Drivers: ${record.get('drivers')}`);
        console.log(`- Sessions: ${record.get('sessions')}`);
        console.log(`- Laps: ${record.get('laps')}`);
        console.log(`- Participation (DROVE_IN): ${record.get('relationships')}`);

    } catch (e) {
        console.error("Error auditing:", e);
    } finally {
        await session.close();
        await driver.close();
    }
}

audit();
