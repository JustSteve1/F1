
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getBigQueryClient } from "@/lib/bq";
import { enforceSqlGuardrails } from "@/lib/pitwall/sqlguardrails";

const DATASET_REF = "f1_data_library_DS";

const BigQuerySearchSchema = z.object({
    limit: z.number().optional().describe("Number of rows to return"),
});

export const get_sample_laps = tool(
    async ({ limit = 25 }) => {
        const sql = `
        SELECT session_id, driver_id, lap_number, lap_time_ms, compound, stint
        FROM \`${DATASET_REF}.laps_clean\`
        ORDER BY session_id DESC, lap_number ASC
        LIMIT ${limit}
    `;
        const bq = getBigQueryClient();
        const [rows] = await bq.query(sql);
        return JSON.stringify(rows);
    },
    {
        name: "get_sample_laps",
        description: "Get raw telemetry for sample laps to analyze lap times, tire compounds, and stints.",
        schema: BigQuerySearchSchema,
    }
);

export const get_qualifying_results = tool(
    async ({ limit = 20 }) => {
        const sql = `
        SELECT 
            d.driver_code, 
            MIN(l.lap_time_ms) as best_lap_time_ms
        FROM \`${DATASET_REF}.laps_clean\` l
        JOIN \`${DATASET_REF}.public_drivers\` d ON l.driver_id = d.driver_id
        WHERE l.session_type = 'Qualifying'
        GROUP BY 1
        ORDER BY 2 ASC
        LIMIT ${limit}
    `;
        const bq = getBigQueryClient();
        const [rows] = await bq.query(sql);
        return JSON.stringify(rows);
    },
    {
        name: "get_qualifying_results",
        description: "Get the best qualifying lap times for each driver in the latest session.",
        schema: BigQuerySearchSchema,
    }
);

export const get_race_results = tool(
    async ({ limit = 20 }) => {
        const sql = `
        SELECT 
            d.driver_code, 
            MAX(l.position) as position,
            MAX(l.lap_number) as laps_completed
        FROM \`${DATASET_REF}.laps_clean\` l
        JOIN \`${DATASET_REF}.public_drivers\` d ON l.driver_id = d.driver_id
        WHERE l.session_type = 'Race'
        GROUP BY 1
        ORDER BY 3 DESC, 2 ASC
        LIMIT ${limit}
    `;
        const bq = getBigQueryClient();
        const [rows] = await bq.query(sql);
        return JSON.stringify(rows);
    },
    {
        name: "get_race_results",
        description: "Get the final race results including position and laps completed for each driver.",
        schema: BigQuerySearchSchema,
    }
);

import { resolve_entity } from "@/app/pitwall/skills/tools/kg_tools";

export const tools = [get_sample_laps, get_qualifying_results, get_race_results, resolve_entity];
