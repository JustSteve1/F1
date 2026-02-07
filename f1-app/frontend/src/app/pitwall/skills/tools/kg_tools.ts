import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getNeo4jSession } from "@/lib/kg/neo4j";

export const resolve_entity = tool(
    async ({ query }) => {
        const session = getNeo4jSession();
        try {
            // Flexible fuzzy search for Drivers or Sessions
            const result = await session.run(`
                CALL db.index.fulltext.queryNodes("driverNames", $query + "~") YIELD node, score
                WHERE score > 0.6
                RETURN node.name as name, node.driver_id as id, labels(node) as type, score
                UNION
                MATCH (s:Session)
                WHERE s.session_id = $query
                RETURN "Session " + s.session_id as name, s.session_id as id, ["Session"] as type, 1.0 as score
                ORDER BY score DESC
                LIMIT 3
            `, { query });

            const matches = result.records.map(r => ({
                name: r.get('name'),
                id: r.get('id'),
                type: r.get('type')[0],
                score: r.get('score')
            }));

            if (matches.length === 0) {
                return "No entities found in Knowledge Graph matching that name.";
            }

            return JSON.stringify(matches);
        } catch (e) {
            console.error("KG Error:", e);
            return "Error querying Knowledge Graph.";
        } finally {
            await session.close();
        }
    },
    {
        name: "resolve_entity",
        description: "Use this to resolve names (e.g. 'Verstappen', 'Monaco') to precise IDs (driver_id, session_id) BEFORE querying BigQuery.",
        schema: z.object({
            query: z.string().describe("The name or term to search for (e.g. 'Max', 'Silverstone')"),
        }),
    }
);
