"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Hammer, Box, Truck } from "lucide-react";

export function FactoryDashboard() {
    return (
        <>
            <div className="mb-6">
                <h1 className="text-4xl font-black uppercase tracking-tighter text-white">Factory</h1>
                <p className="text-white/50 font-light tracking-wide uppercase text-sm">Managing Operations & Development</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 md:gap-6 min-h-[600px]">
                {/* Main Status Tile */}
                <div className="md:col-span-8 lg:col-span-8 row-span-2">
                    <Card className="h-full flex flex-col border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
                        <CardHeader>
                            <CardTitle className="text-xl font-bold uppercase tracking-tight text-white flex items-center gap-2">
                                <Hammer className="h-5 w-5 text-indigo-500" />
                                Production Queue
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="flex-1 flex items-center justify-center">
                            <div className="text-center">
                                <span className="text-4xl font-black text-white block">ACTIVE</span>
                                <span className="text-xs uppercase tracking-widest text-white/40">Chassis MP4-32 Development</span>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Metrics Tile 1 */}
                <div className="md:col-span-4 lg:col-span-4 row-span-1">
                    <Card className="h-full flex flex-col justify-center border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
                        <CardContent className="flex flex-col items-center justify-center py-6">
                            <Box className="h-8 w-8 text-white/50 mb-2" />
                            <span className="text-2xl font-bold text-white">98%</span>
                            <span className="text-[10px] uppercase tracking-widest text-white/40">Efficiency</span>
                        </CardContent>
                    </Card>
                </div>

                {/* Metrics Tile 2 */}
                <div className="md:col-span-4 lg:col-span-4 row-span-1">
                    <Card className="h-full flex flex-col justify-center border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
                        <CardContent className="flex flex-col items-center justify-center py-6">
                            <Truck className="h-8 w-8 text-white/50 mb-2" />
                            <span className="text-2xl font-bold text-white">On Track</span>
                            <span className="text-[10px] uppercase tracking-widest text-white/40">Logistics</span>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </>
    );
}
