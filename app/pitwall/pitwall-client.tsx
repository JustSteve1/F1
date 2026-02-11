
"use client";

import React, { useState } from 'react';

interface PitwallClientProps {
    datasets: string[];
}

interface Table {
    id: string;
    name: string;
    type: string;
}

export default function PitwallClient({ datasets }: PitwallClientProps) {
    const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
    const [tables, setTables] = useState<Table[]>([]);
    const [selectedTable, setSelectedTable] = useState<string | null>(null);
    const [isLoadingTables, setIsLoadingTables] = useState(false);

    // Default URL for the application from env or fallback
    const baseUrl = process.env.NEXT_PUBLIC_VIZ_APP_URL || "https://bigquery-vizualizer-ai-576746898444.us-west1.run.app";

    // Public API Base URL from env or fallback to window.location.origin
    // This is crucial for mixed-content scenarios (HTTPS app -> HTTP localhost)
    const getApiBaseUrl = () => {
        if (process.env.NEXT_PUBLIC_API_BASE_URL) {
            return process.env.NEXT_PUBLIC_API_BASE_URL;
        }
        if (typeof window !== 'undefined') {
            return window.location.origin;
        }
        return '';
    };

    // Construct URL for the iframe:
    // We pass ?dataset=[URL_TO_OUR_API]
    // Our API: [API_BASE]/api/bq-data?datasetId=X&tableId=Y
    const getIframeSrc = () => {
        if (selectedDataset && selectedTable) {
            const apiBase = getApiBaseUrl();
            const apiUrl = `${apiBase}/api/bq-data?datasetId=${selectedDataset}&tableId=${selectedTable}`;
            return `${baseUrl}?dataset=${encodeURIComponent(apiUrl)}`;
        }
        return baseUrl;
    };

    const handleDatasetClick = async (datasetId: string) => {
        if (selectedDataset === datasetId) {
            setSelectedDataset(null); // Toggle off if clicked again
            setTables([]);
            return;
        }

        setSelectedDataset(datasetId);
        setSelectedTable(null); // Reset table selection
        setIsLoadingTables(true);
        setTables([]);

        try {
            const response = await fetch(`/api/bq-structure?datasetId=${datasetId}&tables=true`);
            if (response.ok) {
                const data = await response.json();
                setTables(data);
            } else {
                console.error("Failed to fetch tables");
            }
        } catch (error) {
            console.error("Error loading tables:", error);
        } finally {
            setIsLoadingTables(false);
        }
    };

    const handleTableClick = (tableName: string) => {
        setSelectedTable(tableName);
    };

    return (
        <div className="flex h-screen w-full bg-black text-white">
            <aside className="w-64 border-r border-gray-800 flex flex-col hidden md:flex">
                <div className="p-4 border-b border-gray-800">
                    <h2 className="text-xl font-bold text-indigo-400">Pitwall</h2>
                    <p className="text-xs text-gray-500 mt-1">Select a table to load</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                    <h3 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wider">Available Datasets</h3>
                    {datasets.length > 0 ? (
                        <ul className="space-y-4">
                            {datasets.map((datasetId) => (
                                <li key={datasetId} className="group">
                                    <div
                                        onClick={() => handleDatasetClick(datasetId)}
                                        className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${selectedDataset === datasetId ? 'text-indigo-300 font-medium' : 'text-gray-300 hover:text-white'
                                            }`}
                                    >
                                        <span className="truncate" title={datasetId}>{datasetId}</span>
                                        <span className={`text-xs transform transition-transform ${selectedDataset === datasetId ? 'rotate-90' : ''}`}>▶</span>
                                    </div>

                                    {/* Tables List */}
                                    {selectedDataset === datasetId && (
                                        <div className="ml-2 mt-1 pl-2 border-l border-gray-700">
                                            {isLoadingTables ? (
                                                <div className="text-xs text-gray-500 py-1 pl-2">Loading tables...</div>
                                            ) : tables.length > 0 ? (
                                                <ul className="space-y-1">
                                                    {tables.map(table => (
                                                        <li
                                                            key={table.id}
                                                            onClick={() => handleTableClick(table.name)}
                                                            className={`text-sm py-1 px-2 rounded cursor-pointer truncate transition-colors ${selectedTable === table.name
                                                                    ? 'bg-indigo-600/30 text-indigo-200'
                                                                    : 'text-gray-400 hover:text-gray-200'
                                                                }`}
                                                            title={table.name}
                                                        >
                                                            {table.name}
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <div className="text-xs text-gray-500 py-1 pl-2">No tables found</div>
                                            )}
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div className="text-gray-500 text-sm italic">No datasets found.</div>
                    )}
                </div>

                <div className="p-4 border-t border-gray-800 text-xs text-gray-600">
                    <p>Selecting a table auto-loads it into the visualizer.</p>
                </div>
            </aside>

            <main className="flex-1 flex flex-col relative bg-gray-900">
                <iframe
                    key={getIframeSrc()} // Force re-render on src change
                    src={getIframeSrc()}
                    className="flex-grow w-full border-0"
                    title="BigQuery Visualizer AI"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; camera; microphone"
                    allowFullScreen
                />
            </main>
        </div>
    );
}
