import { NextResponse } from "next/server";
import { getBigQueryClient } from "@/lib/bq";
import { enforceSqlGuardrails } from "@/lib/pitwall/sqlGuardrails";

const DATASET_REF = "f1-data-library.f1_data_library_DS";

function getAllowlist() {
    return (process.env.BIGQUERY_ALLOWLIST_TABLES || "laps_clean,public_session_data_audit")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
}

export async function GET(req: Request) {
    try {
        const url = new URL(req.url);
        const name = url.searchParams.get("name");

        if (!name) return NextResponse.json({ error: "Missing view name" }, { status: 400 });

        let sqlRaw = "";

        switch (name) {
            case "sample_laps":
                sqlRaw = `
                    SELECT session_id, driver_id, lap_number, lap_time_ms, compound, stint
                    FROM \`${DATASET_REF}.laps_clean\`
                    ORDER BY session_id DESC, lap_number ASC
                    LIMIT 25
                `;
                break;
            case "qualifying_results":
                // Best lap per driver in Qualifying
                sqlRaw = `
                    SELECT 
                        d.driver_code, 
                        MIN(l.lap_time_ms) as best_lap_time_ms
                    FROM \`${DATASET_REF}.laps_clean\` l
                    JOIN \`${DATASET_REF}.public_drivers\` d ON l.driver_id = d.driver_id
                    WHERE l.session_type = 'Qualifying'
                    GROUP BY 1
                    ORDER BY 2 ASC
                    LIMIT 20
                `;
                break;
            case "race_results":
                // Final position (proxy)
                sqlRaw = `
                    SELECT 
                        d.driver_code, 
                        MAX(l.position) as position,
                        MAX(l.lap_number) as laps_completed
                    FROM \`${DATASET_REF}.laps_clean\` l
                    JOIN \`${DATASET_REF}.public_drivers\` d ON l.driver_id = d.driver_id
                    WHERE l.session_type = 'Race'
                    GROUP BY 1
                    ORDER BY 3 DESC, 2 ASC
                    LIMIT 20
                 `;
                break;
            default:
                return NextResponse.json({ error: `Unknown view: ${name}` }, { status: 400 });
        }

        const sql = enforceSqlGuardrails(sqlRaw, {
            allowlistTables: getAllowlist(),
            defaultLimit: Number(process.env.BIGQUERY_DEFAULT_LIMIT || 1000),
            maxLimit: 1000,
        });

        const bq = getBigQueryClient();
        const [job] = await bq.createQueryJob({
            query: sql,
            location: process.env.BIGQUERY_LOCATION || "EU",
        });

        const [rows] = await job.getQueryResults();
        const stats = job.metadata?.statistics?.query || {};
        const bytesProcessed = Number(stats.totalBytesProcessed || 0);

        const columns = rows.length ? Object.keys(rows[0] as Record<string, unknown>) : [];

        return NextResponse.json({
            rows,
            rowCount: rows.length,
            bytesProcessed,
            columns,
        });
    } catch (err: any) {
        return NextResponse.json(
            { error: err?.message || "Unknown error" },
            { status: 400 }
        );
    }
}
