
import { BigQuery } from '@google-cloud/bigquery';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const datasetId = searchParams.get('datasetId');
    const tableId = searchParams.get('tableId');
    const query = searchParams.get('query');

    // CORS headers to allow the external app to fetch this data
    const headers = {
        'Access-Control-Allow-Origin': '*', // In production, restrict this to the specific app domain
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Allow-Private-Network': 'true', // Needed for requests from public internet to localhost
    };

    if (request.method === 'OPTIONS') {
        return NextResponse.json({}, { headers });
    }

    try {
        const bigquery = new BigQuery();
        let rows: any[] = [];

        if (query) {
            const [queryRows] = await bigquery.query({ query });
            rows = queryRows;
        } else if (datasetId && tableId) {
            // Using a SQL query supports both Tables and Views
            // construct the fully qualified name safely
            const sqlQuery = `SELECT * FROM \`${datasetId}.${tableId}\` LIMIT 1000`;
            const [queryRows] = await bigquery.query({ query: sqlQuery });
            rows = queryRows;
        } else {
            return NextResponse.json(
                { error: 'Missing required parameters: (datasetId AND tableId) OR query' },
                { status: 400, headers }
            );
        }

        // Flatten rows to avoid nested object issues in the visualizer
        return NextResponse.json(rows.map(row => flattenObject(row)), { headers });
    } catch (error: any) {
        console.error('BigQuery API Error:', error);
        return NextResponse.json(
            { error: error.message || 'Internal Server Error' },
            { status: 500, headers }
        );
    }
}

// Helper to flatten nested BigQuery struct objects
function flattenObject(obj: any, prefix = '', res: any = {}) {
    for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
            const val = obj[key];
            const newKey = prefix ? `${prefix}_${key}` : key;
            if (val && typeof val === 'object' && !Array.isArray(val) && !(val instanceof Date) && val.constructor.name !== 'Buffer') {
                flattenObject(val, newKey, res);
            } else {
                res[newKey] = val;
            }
        }
    }
    return res;
}

export async function OPTIONS() {
    return NextResponse.json({}, {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Private-Network': 'true',
        }
    });
}
