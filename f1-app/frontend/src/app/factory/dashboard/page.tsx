"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";

const API_BASE = "http://localhost:8000";

export default function FactoryDashboard() {
    const [videos, setVideos] = useState<any[]>([]);
    const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
    const [loadingVideos, setLoadingVideos] = useState(false);

    useEffect(() => {
        fetchVideos();
    }, []);

    const fetchVideos = async () => {
        setLoadingVideos(true);
        try {
            const res = await fetch(`${API_BASE}/api/factory/videos`);
            const data = await res.json();
            setVideos(data.videos || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoadingVideos(false);
        }
    };

    const [analysisRunId, setAnalysisRunId] = useState<string | null>(null);
    const [analysisResult, setAnalysisResult] = useState<any | null>(null);
    const [analyzing, setAnalyzing] = useState(false);

    const handleRunAnalysis = async () => {
        if (!selectedVideo) return;
        setAnalyzing(true);
        setAnalysisResult(null); // Clear previous

        try {
            const res = await fetch(`${API_BASE}/api/factory/telemetry-analysis`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ video_uri: selectedVideo })
            });
            const data = await res.json();
            setAnalysisRunId(data.run_id);
            alert(`Analysis Started: ${data.run_id}`);
        } catch (e) {
            alert(`Analysis Error: ${e}`);
        } finally {
            setAnalyzing(false);
        }
    };

    const checkAnalysisStatus = async () => {
        if (!analysisRunId) return;
        try {
            // Poll for status
            const res = await fetch(`${API_BASE}/api/factory/run?run_id=${analysisRunId}`);
            const data = await res.json();

            if (data.status === "DONE") {
                setAnalysisResult(data.output_refs_json);
            } else {
                alert(`Status: ${data.status}`);
            }
        } catch (e) {
            alert(`Check Error: ${e}`);
        }
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-mono">
            <div className="flex justify-between items-center mb-8 border-b border-gray-700 pb-4">
                <h1 className="text-3xl font-bold">Factory Dashboard</h1>
                <Link href="/factory" className="text-green-500 hover:text-green-400 text-sm">
                    &larr; Back to Factory
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg">
                    <h2 className="text-xl font-bold mb-4 text-purple-500">System Status</h2>
                    <div className="flex items-center gap-2 text-sm mb-6">
                        <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                        <span className="text-gray-300">Backend Online</span>
                    </div>

                    <h2 className="text-xl font-bold mb-4 text-orange-500">Video Library</h2>
                    <p className="text-gray-400 text-sm mb-4">Select a video from the specific Bitbucket (GCS) folder.</p>

                    <div className="mb-6">
                        {loadingVideos ? (
                            <div className="text-gray-500 animate-pulse">Loading videos...</div>
                        ) : (
                            <select
                                className="w-full bg-black text-white border border-gray-700 rounded p-2 text-sm mb-2"
                                onChange={(e) => setSelectedVideo(e.target.value)}
                                value={selectedVideo || ""}
                            >
                                <option value="">-- Select a Video --</option>
                                {videos.map((v) => (
                                    <option key={v.uri} value={v.uri}>
                                        {v.name} ({Math.round(v.size / 1024 / 1024)}MB)
                                    </option>
                                ))}
                            </select>
                        )}
                        <button onClick={fetchVideos} className="text-xs text-blue-500 underline ml-1">Refresh List</button>
                    </div>

                    {selectedVideo && (
                        <div className="mt-6 border-t border-gray-800 pt-4">
                            <div className="text-xs text-green-400 font-mono break-all mb-4">
                                Selected: {selectedVideo}
                            </div>

                            <button
                                onClick={handleRunAnalysis}
                                disabled={analyzing}
                                className={`w-full font-bold py-2 px-4 rounded transition mb-2 ${analyzing ? "bg-gray-600 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 text-white"}`}
                            >
                                {analyzing ? "Starting..." : "Run Telemetry Analysis"}
                            </button>

                            {analysisRunId && (
                                <div className="text-xs text-gray-500 mb-4 mt-2 p-2 bg-black rounded border border-gray-800">
                                    Run ID: <span className="text-yellow-500">{analysisRunId}</span>
                                    <button onClick={checkAnalysisStatus} className="ml-4 underline text-blue-400 hover:text-blue-300">Check Status</button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg flex flex-col">
                    <h2 className="text-xl font-bold mb-4 text-yellow-500">Analysis Results</h2>
                    <div className="bg-black border border-gray-800 rounded p-4 flex-1 overflow-auto h-96 font-mono text-xs text-green-400">
                        {analysisResult ? (
                            <div className="space-y-2">
                                <div className="text-gray-500 mb-2">--- Analysis Result ---</div>
                                <pre className="whitespace-pre-wrap">{JSON.stringify(analysisResult, null, 2)}</pre>
                            </div>
                        ) : (
                            <span className="text-gray-600">Select a video and run analysis to see telemetry JSON.</span>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
