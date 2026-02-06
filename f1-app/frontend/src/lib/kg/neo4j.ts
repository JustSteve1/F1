
import neo4j, { Driver, Session } from 'neo4j-driver';

let driver: Driver | null = null;

const NEO4J_URI = process.env.NEO4J_URI || 'bolt://localhost:7687';
const NEO4J_USER = process.env.NEO4J_USER || 'neo4j';
const NEO4J_PASSWORD = process.env.NEO4J_PASSWORD || 'password';

export function getNeo4jDriver(): Driver {
    if (!driver) {
        driver = neo4j.driver(
            NEO4J_URI,
            neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD),
            {
                disableLosslessIntegers: true // Simplify JS integer handling
            }
        );
        console.log("⚡ Neo4j Driver Initialized");
    }
    return driver;
}

export function getNeo4jSession(): Session {
    return getNeo4jDriver().session();
}

// Cleanup on shutdown (optional, mainly for dev HMR)
if (process.env.NODE_ENV !== 'production') {
    // In dev, nextjs might re-import this file, keeping connections open.
    // Ideally we attach to global, but for now this singleton pattern works per module instance.
}
