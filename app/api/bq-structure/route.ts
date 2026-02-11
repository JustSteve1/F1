
import { BigQuery } from '@google-cloud/bigquery';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams;
    const datasetId = searchParams.get('datasetId'); // Get tables for a dataset
    const includeTables = searchParams.get('tables') === 'true'; // Optionally list tables for all datasets

    try {
        const bigquery = new BigQuery();

        if (includeTables && datasetId) {
            // Fetch tables for a specific dataset
            const [tables] = await bigquery.dataset(datasetId).getTables();
            return NextResponse.json(tables.map((table: any) => ({
                id: table.id,
                name: table.metadata.tableReference.tableId,
                type: table.metadata.type,
            })));
        } else {
            // Fetch all datasets
            // This is actually what's happening server-side in page.tsx already,
            // but maybe the client needs it too?
            // Let's implement getting datasets here just in case.
            const [datasets] = await bigquery.getDatasets();
            return NextResponse.json(datasets.map((ds: any) => ({
                id: ds.id,
                description: ds.metadata?.description
            })));
        }
    } catch (error: any) {
        console.error('BigQuery Structure Error:', error);
        return NextResponse.json(
            { error: error.message || 'Internal Server Error' },
            { status: 500 }
        );
    }
}
