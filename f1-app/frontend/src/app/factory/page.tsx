
"use client"

import React, { useState, useRef } from 'react';

export default function FactoryPage() {
    const [analyzing, setAnalyzing] = useState(false);
    const [log, setLog] = useState<string>("");
    const [file, setFile] = useState<File | null>(null);
    const [filePreview, setFilePreview] = useState<string | null>(null);

    const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selected = e.target.files[0];
            setFile(selected);
            setFilePreview(URL.createObjectURL(selected));
            setLog(""); // Clear previous logs
        }
    };

    const handleAnalyze = async () => {
        if (!file || analyzing) return;
        setAnalyzing(true);
        setLog("// Initializing Model: gemini-2.0-flash-exp...\n// Uploading Video to Context...");

        const formData = new FormData();
        formData.append("video", file);
        formData.append("prompt", "Analyze this video for race incidents or technical compliance.");

        try {
            const response = await fetch("/api/factory/analyze", {
                method: "POST",
                body: formData,
            });

            if (!response.body) throw new Error("No stream body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const text = decoder.decode(value);
                setLog(prev => prev + text);
            }
        } catch (err: any) {
            setLog(prev => prev + "\n\n❌ Error: " + err.message);
        } finally {
            setAnalyzing(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-[#0E0E0E] text-white p-6 overflow-hidden relative">
            {/* Background Ambience */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-[#050505] to-[#000000] pointer-events-none" />

            <div className="relative z-10 flex flex-col h-full max-w-7xl mx-auto w-full gap-6">
                {/* Header */}
                <header className="flex items-center justify-between py-4 border-b border-white/5">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-blue-600/20 flex items-center justify-center border border-blue-500/30">
                            <span className="text-xl">🏭</span>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold tracking-tight">The Factory</h1>
                            <p className="text-xs text-gray-500 font-mono uppercase tracking-widest">Video Intelligence Unit</p>
                        </div>
                    </div>
                    <div>
                        <a href="/" className="text-xs text-gray-500 hover:text-white transition-colors">Back to Hub</a>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1 min-h-0">
                    {/* Left Panel: Upload & Preview */}
                    <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4 border border-white/10 bg-white/5 backdrop-blur-md">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">Input Source</h2>

                        {!filePreview ? (
                            <label className="flex-1 border-2 border-dashed border-white/10 rounded-xl flex items-center justify-center hover:border-blue-500/50 transition-colors cursor-pointer group bg-black/20 relative">
                                <input type="file" accept="video/mp4,video/quicktime,video/webm" className="hidden" onChange={handleFile} />
                                <div className="text-center p-8">
                                    <div className="w-16 h-16 rounded-full bg-zinc-900 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
                                        <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                        </svg>
                                    </div>
                                    <p className="text-lg font-medium text-gray-200">Drop Analysis Video</p>
                                    <p className="text-sm text-gray-500 mt-2">MP4, MOV (Max 5 mins)</p>
                                </div>
                            </label>
                        ) : (
                            <div className="flex-1 relative rounded-xl overflow-hidden bg-black border border-white/10">
                                <video src={filePreview} controls className="w-full h-full object-contain" />
                                <button
                                    onClick={() => { setFile(null); setFilePreview(null); setLog(""); }}
                                    className="absolute top-4 right-4 bg-black/50 hover:bg-red-500/50 text-white rounded-full p-2 backdrop-blur-md transition-colors"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                </button>
                            </div>
                        )}

                        <button
                            onClick={handleAnalyze}
                            disabled={!file || analyzing}
                            className="w-full py-4 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-gray-500 disabled:cursor-not-allowed rounded-xl font-bold uppercase tracking-widest transition-all hover:shadow-[0_0_20px_rgba(37,99,235,0.3)] flex items-center justify-center gap-2"
                        >
                            {analyzing ? (
                                <>
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Analyzing with Gemini 3...
                                </>
                            ) : (
                                <>
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    Run Analysis
                                </>
                            )}
                        </button>
                    </div>

                    {/* Right Panel: Agent Log & Output */}
                    <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4 border border-white/10 bg-white/5 backdrop-blur-md">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold uppercase tracking-wider text-gray-400">Gemini 3 Analysis Log</h2>
                            <div className="flex gap-1.5">
                                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse [animation-delay:0.2s]" />
                                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse [animation-delay:0.4s]" />
                            </div>
                        </div>

                        <div className="flex-1 bg-black/40 rounded-xl p-4 font-mono text-sm text-green-400/80 overflow-y-auto border border-white/5 shadow-inner whitespace-pre-wrap">
                            {log || <span className="opacity-50">// System Ready. Waiting for input...</span>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
