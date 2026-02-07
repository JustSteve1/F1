"use client"

import { useState } from "react"
import type { VisualizationSpec } from 'react-vega';
import { PitwallChat } from "./components/PitwallChat"
import { PitwallViz } from "./components/PitwallViz"

export default function PitwallPage() {
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([
        { role: 'assistant', content: 'Welcome to the Pitwall. Ask me anything about the data (Qualifying, Race, Telemetry).' }
    ])
    const [vizSpec, setVizSpec] = useState<VisualizationSpec | null>(null)
    const [loading, setLoading] = useState(false)

    const handleSendMessage = async (prompt: string) => {
        setMessages(prev => [...prev, { role: 'user', content: prompt }])
        setLoading(true)
        setVizSpec(null)

        try {
            // Simplified: No more Layer 1 fetch. The Agent does it all.
            const vizRes = await fetch('/api/pitwall/viz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            })

            if (!vizRes.ok) {
                const errText = await vizRes.text();
                let errMsg = "Failed to generate viz";
                try { errMsg = JSON.parse(errText).error || errMsg } catch { }
                throw new Error(errMsg);
            }

            const vizData = await vizRes.json()

            // Handle array wrapping
            const spec = Array.isArray(vizData) ? vizData[0].vegaLiteSpec : vizData.vegaLiteSpec;
            const explanation = Array.isArray(vizData) ? vizData[0].explanation : vizData.explanation;

            if (spec) {
                setVizSpec(spec)
            } else {
                setVizSpec(null)
            }

            setMessages(prev => [...prev, { role: 'assistant', content: explanation || "Visualization generated." }])

        } catch (err: any) {
            console.error(err)
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
        } finally {
            setLoading(false)
        }
    }

    return (
        <main className="h-screen w-screen bg-[#050505] text-white p-4 md:p-6 lg:p-8 flex flex-col gap-6 overflow-hidden relative">
            {/* Background Ambience */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-red-900/10 blur-[120px] rounded-full pointer-events-none"></div>
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-blue-900/10 blur-[120px] rounded-full pointer-events-none"></div>

            {/* Top Bar */}
            <header className="flex items-center justify-between shrink-0 z-10">
                <div className="flex items-center gap-4">
                    <div className="font-mono text-2xl font-bold tracking-tighter f1-gradient-text">
                        F1<span className="text-red-600">.</span>DATA
                    </div>
                    <div className="h-6 w-px bg-white/10"></div>
                    <div className="text-xs text-gray-500 font-mono tracking-widest uppercase">Pitwall v2.0 (Agentic)</div>
                </div>

                <div className="flex gap-4 text-xs font-mono text-gray-500 hidden md:flex">
                    <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 box-shadow-green"></span>
                        AGENT ONLINE
                    </div>
                </div>
            </header>

            {/* Main Dashboard Layout */}
            <div className="flex-1 flex flex-col md:flex-row gap-6 min-h-0 z-10">

                {/* Left Panel: Chat */}
                <div className="w-full md:w-1/3 lg:w-1/4 min-w-[320px] flex flex-col">
                    <PitwallChat
                        messages={messages}
                        loading={loading}
                        onSendMessage={handleSendMessage}
                    />
                </div>

                {/* Right Panel: Visualization */}
                <div className="flex-1 flex flex-col min-w-0">
                    <PitwallViz
                        spec={vizSpec}
                        loading={loading}
                    />
                </div>
            </div>
        </main>
    )
}
