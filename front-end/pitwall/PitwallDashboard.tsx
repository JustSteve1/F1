"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Zap, Signal } from "lucide-react";

export function PitwallDashboard() {
    return (
        <>
            <div className="mb-6">
                <h1 className="text-4xl font-black uppercase tracking-tighter text-white">Pitwall</h1>
                <p className="text-white/50 font-light tracking-wide uppercase text-sm">Real-time Telemetry & Strategy</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 md:gap-6 min-h-[600px]">

                {/* Telemetry Main Display */}
                <div className="md:col-span-12 lg:col-span-8 row-span-2">
                    <Card className="h-full flex flex-col border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500 relative overflow-hidden">
                        <div className="absolute inset-0 bg-[url('/images/grid.png')] opacity-5" />
                        <CardHeader>
                            <CardTitle className="text-xl font-bold uppercase tracking-tight text-white flex items-center gap-2">
                                <Activity className="h-5 w-5 text-red-500" />
                                Live Telemetry
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 flex items-end justify-between p-6">
                            {/* Fake graph bars */}
                            <div className="w-4 h-24 bg-white/20 rounded-t-sm"></div>
                            <div className="w-4 h-32 bg-white/40 rounded-t-sm"></div>
                            <div className="w-4 h-16 bg-white/20 rounded-t-sm"></div>
                            <div className="w-4 h-40 bg-white/60 rounded-t-sm"></div>
                            <div className="w-4 h-28 bg-white/30 rounded-t-sm"></div>
                            <div className="w-4 h-36 bg-white/50 rounded-t-sm"></div>
                            <div className="w-4 h-12 bg-white/10 rounded-t-sm"></div>
                            <div className="w-4 h-44 bg-indigo-500 rounded-t-sm animate-pulse"></div>
                            <div className="w-4 h-30 bg-white/40 rounded-t-sm"></div>
                        </CardContent>
                    </Card>
                </div>

                {/* Strategy Stat 1 */}
                <div className="md:col-span-6 lg:col-span-4 row-span-1">
                    <Card className="h-full flex flex-col justify-center border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
                        <CardContent className="flex flex-row items-center justify-between p-6">
                            <div>
                                <span className="block text-3xl font-black text-white">1:24.5</span>
                                <span className="text-[10px] uppercase tracking-widest text-white/40">Last Lap</span>
                            </div>
                            <Zap className="h-8 w-8 text-yellow-500" />
                        </CardContent>
                    </Card>
                </div>

                {/* Strategy Stat 2 */}
                <div className="md:col-span-6 lg:col-span-4 row-span-1">
                    <Card className="h-full flex flex-col justify-center border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
                        <CardContent className="flex flex-row items-center justify-between p-6">
                            <div>
                                <span className="block text-3xl font-black text-white">HARD</span>
                                <span className="text-[10px] uppercase tracking-widest text-white/40">Tyre Compound</span>
                            </div>
                            <Signal className="h-8 w-8 text-green-500" />
                        </CardContent>
                    </Card>
                </div>
            </div>
        </>
    );
}
