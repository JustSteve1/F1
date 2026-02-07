"use client"

import dynamic from 'next/dynamic'

// Dynamic import with NO SSR to prevent hydration issues
// @ts-ignore
const Vega = dynamic(() => import('react-vega').then((mod) => mod.VegaEmbed), { ssr: false });

interface PitwallVizProps {
    spec: any
    loading: boolean
}

export function PitwallViz({ spec, loading }: PitwallVizProps) {
    return (
        <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden shadow-2xl relative">
            {/* Header */}
            <div className="p-4 border-b border-white/10 bg-black/40 backdrop-blur-md flex items-center justify-between z-10">
                <h2 className="font-bold text-sm tracking-widest text-white/90 uppercase">Telemetry Visualization</h2>
                <div className="flex gap-2">
                    <span className="w-3 h-3 rounded-full bg-zinc-700 border border-zinc-600"></span>
                    <span className="w-3 h-3 rounded-full bg-zinc-700 border border-zinc-600"></span>
                </div>
            </div>

            {/* Canvas Area */}
            <div className="flex-1 relative bg-gradient-to-br from-zinc-900 to-black flex items-center justify-center p-6 overflow-hidden">

                {/* Background Grid Effect */}
                <div className="absolute inset-0 opacity-10 pointer-events-none"
                    style={{ backgroundImage: 'radial-gradient(circle, #333 1px, transparent 1px)', backgroundSize: '20px 20px' }}>
                </div>

                {loading ? (
                    <div className="text-center animate-pulse">
                        <div className="text-4xl mb-4">🏎️</div>
                        <div className="text-sm text-gray-400 font-mono">Processing telemetry...</div>
                    </div>
                ) : spec ? (
                    <div className="w-full h-full animate-fade-in flex items-center justify-center">
                        <Vega
                            spec={spec}
                            options={{
                                actions: false,
                                theme: 'dark',
                                renderer: 'svg',
                                background: 'transparent'
                            }}
                            className="w-full h-full flex items-center justify-center"
                        />
                    </div>
                ) : (
                    <div className="text-center text-gray-500">
                        <div className="text-6xl mb-4 opacity-20">📊</div>
                        <p className="text-sm font-light">Waiting for query...</p>
                    </div>
                )}
            </div>

            {/* Footer / Context */}
            {spec && (
                <div className="absolute bottom-4 right-4 bg-black/60 backdrop-blur px-3 py-1 rounded border border-white/10 text-[10px] text-gray-400 font-mono">
                    VEGA-LITE RENDERER ACTIVE
                </div>
            )}
        </div>
    )
}
