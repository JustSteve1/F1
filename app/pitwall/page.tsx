
import { BigQuery } from '@google-cloud/bigquery';
import React from 'react';
import PitwallClient from './pitwall-client';

async function getDatasets() {
    try {
        const bigquery = new BigQuery();
        const [datasets] = await bigquery.getDatasets();
        return datasets.map((dataset) => dataset.id);
    } catch (error) {
        // Log the error for debugging purposes
        console.error("Error fetching BigQuery datasets:", error);
        return [];
    }
}

export default async function PitwallPage() {
    const datasets = await getDatasets();

    return (
        <PitwallClient datasets={datasets} />
    );
}
