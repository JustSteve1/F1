"use client";

import { useState, useRef } from "react";

const API_BASE = "http://localhost:8000";

export default function FactoryPage() {
    // Input State
    const [trackId, setTrackId] = useState("monza");

    const [video1, setVideo1] = useState({
        source_type: "F1_REAL",
        uri: "gs://f1-data-library/videos/monza_2024_lec.mp4",
        lap_hint: "",
        anchors_text: ""
    });

    const [video2, setVideo2] = useState({
        source_type: "SIM",
        uri: "gs://f1-data-library/videos/monza_sim_steve.mp4",
        lap_hint: "",
        anchors_text: ""
    });

    // Run State
    const [syncRunId, setSyncRunId] = useState<string | null>(null);



    const [statusLog, setStatusLog] = useState<string[]>([]);
    const [uploading, setUploading] = useState(false);

    const fileInputRef1 = useRef<HTMLInputElement>(null);
    const fileInputRef2 = useRef<HTMLInputElement>(null);

    const log = (msg: string) => setStatusLog(prev => [...prev, `${new Date().toLocaleTimeString()}: ${msg}`]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: "REF" | "SIM") => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];

        setUploading(true);
        log(`Uploading ${file.name}...`);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch(`${API_BASE}/api/factory/upload?type=${type}`, {
                method: "POST",
                body: formData,
            });
            if (!res.ok) throw new Error("Upload failed");

            const data = await res.json();
            const uri = data.uri;
            log(`Uploaded: ${uri}`);

            if (type === "REF") {
                setVideo1(prev => ({ ...prev, uri }));
            } else {
                setVideo2(prev => ({ ...prev, uri }));
            }
        } catch (err) {
            log(`Upload Error: ${err}`);
        } finally {
            setUploading(false);
            // Reset input so same file can be selected again if needed
            e.target.value = "";
        }
    };

    const [verificationResults, setVerificationResults] = useState<any[]>([]);

    const handleVerification = async () => {
        log("Starting Verification...");
        setVerificationResults([]);
        try {
            const res = await fetch(`${API_BASE}/api/factory/verify-sync`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    track_id: trackId,
                    videos: [video1, video2]
                })
            });
            const data = await res.json();
            setSyncRunId(data.run_id);
            log(`Verification Run Started: ${data.run_id}`);
        } catch (e) {
            log(`Error: ${e}`);
        }
    };

    const checkRunStatus = async (runId: string) => {
        try {
            const res = await fetch(`${API_BASE}/api/factory/run?run_id=${runId}`);
            const data = await res.json();
            log(`Run ${runId} Status: ${data.status}`);

            if (data.status === "DONE" && data.output_refs_json) {
                const out = data.output_refs_json;
                if (out.items) {
                    setVerificationResults(out.items);
                    log("Verification results loaded.");
                }
            } else if (data.status === "ERROR") {
                log(`Error in run: ${data.error}`);
            }
        } catch (e) {
            log(`Check failed: ${e}`);
        }
    }

    return (
        <div className="min-h-screen bg-black text-white p-8 font-mono">
            <h1 className="text-3xl font-bold mb-8 border-b border-gray-700 pb-4">F1 Factory Agent</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Left Column: Inputs */}
                <div className="space-y-6">

                    <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg">
                        <h2 className="text-xl font-bold mb-4 text-green-500">1. Setup</h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-1">Track ID</label>
                                <input
                                    type="text"
                                    value={trackId}
                                    onChange={e => setTrackId(e.target.value)}
                                    className="w-full bg-black border border-gray-700 p-2 rounded focus:border-green-500 outline-none"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold text-blue-500">2. Reference Video (F1)</h2>
                            <button
                                onClick={() => fileInputRef1.current?.click()}
                                disabled={uploading}
                                className="bg-gray-800 hover:bg-gray-700 text-xs px-3 py-1 rounded border border-gray-700 transition"
                            >
                                {uploading ? "Importing..." : "Import Video"}
                            </button>
                            <input
                                type="file"
                                ref={fileInputRef1}
                                onChange={e => handleFileUpload(e, "REF")}
                                className="hidden"
                                accept="video/*"
                            />
                        </div>
                        <div className="space-y-4">
                            <input type="text" value={video1.uri} onChange={e => setVideo1({ ...video1, uri: e.target.value })} className="w-full bg-black border border-gray-700 p-2 rounded" placeholder="gs://..." />
                            <input type="text" value={video1.lap_hint} onChange={e => setVideo1({ ...video1, lap_hint: e.target.value })} className="w-full bg-black border border-gray-700 p-2 rounded" placeholder="Lap Hint (e.g. starts at 0:15)" />
                        </div>
                    </div>

                    <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold text-purple-500">3. Sim Video (User)</h2>
                            <button
                                onClick={() => fileInputRef2.current?.click()}
                                disabled={uploading}
                                className="bg-gray-800 hover:bg-gray-700 text-xs px-3 py-1 rounded border border-gray-700 transition"
                            >
                                {uploading ? "Importing..." : "Import Video"}
                            </button>
                            <input
                                type="file"
                                ref={fileInputRef2}
                                onChange={e => handleFileUpload(e, "SIM")}
                                className="hidden"
                                accept="video/*"
                            />
                        </div>
                        <div className="space-y-4">
                            <input type="text" value={video2.uri} onChange={e => setVideo2({ ...video2, uri: e.target.value })} className="w-full bg-black border border-gray-700 p-2 rounded" placeholder="gs://..." />
                            <input type="text" value={video2.lap_hint} onChange={e => setVideo2({ ...video2, lap_hint: e.target.value })} className="w-full bg-black border border-gray-700 p-2 rounded" placeholder="Lap Hint" />
                        </div>
                    </div>



                </div>

                {/* Right Column: Verification & Status */}
                <div className="space-y-6">
                    <div className="bg-gray-900 ring-1 ring-gray-800 p-6 rounded-lg">
                        <h2 className="text-xl font-bold mb-4 text-yellow-500">Verification</h2>

                        <div className="space-y-6">
                            {/* Verification Step */}
                            <button
                                onClick={handleVerification}
                                disabled={!video1.uri || !video2.uri}
                                className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold py-3 px-4 rounded transition mb-4"
                            >
                                START VERIFICATION
                            </button>

                            {syncRunId && (
                                <div className="text-xs font-mono text-gray-500 mb-2">
                                    Run ID: {syncRunId} <button onClick={() => checkRunStatus(syncRunId)} className="ml-2 underline">Refresh</button>
                                </div>
                            )}

                            {/* Results Grid */}
                            {verificationResults.length > 0 && (
                                <div className="border border-gray-800 rounded bg-black/50 overflow-hidden">
                                    <table className="w-full text-xs text-left text-gray-400">
                                        <thead className="bg-gray-800 text-gray-200">
                                            <tr>
                                                <th className="p-2">Time</th>
                                                <th className="p-2">Ref Time</th>
                                                <th className="p-2">Sim Time</th>
                                                <th className="p-2">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {verificationResults.map((row, i) => (
                                                <tr key={i} className="border-b border-gray-800">
                                                    <td className="p-2 font-mono">{row.label}</td>
                                                    <td className="p-2 font-mono text-blue-400">{row.ref_time_read}</td>
                                                    <td className="p-2 font-mono text-purple-400">{row.sim_time_read}</td>
                                                    <td className="p-2">
                                                        {row.ref_time_read !== "N/A" && row.sim_time_read !== "N/A" ? (
                                                            <span className="text-green-500">OK</span>
                                                        ) : (
                                                            <span className="text-red-500">Retry</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="bg-black border border-gray-800 p-4 rounded-lg h-64 overflow-y-auto font-mono text-xs">
                        <h3 className="text-gray-500 mb-2 sticky top-0 bg-black pb-2 border-b border-gray-800">System Log</h3>
                        {statusLog.map((l, i) => (
                            <div key={i} className="mb-1 text-gray-400">{l}</div>
                        ))}
                    </div>

                </div>
            </div>
        </div>
    );
}
