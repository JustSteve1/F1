"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Flag, Trophy } from "lucide-react";

export function WelcomeTile({ userEmail }: { userEmail?: string | null }) {
    return (
        <Card className="h-full flex flex-col justify-between border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
            <CardHeader>
                <div className="space-y-1">
                    <CardTitle className="text-3xl font-black uppercase tracking-tighter text-white">
                        Welcome Back
                    </CardTitle>
                    <CardDescription className="text-white/60 font-light tracking-wide uppercase text-xs">
                        {userEmail || "PILOT"}
                    </CardDescription>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-sm border border-white/10 bg-black/20 text-center">
                        <Flag className="h-6 w-6 text-white/50 mx-auto mb-2" />
                        <div className="text-2xl font-black text-white">12</div>
                        <div className="text-[10px] uppercase tracking-widest text-white/40">Races</div>
                    </div>
                    <div className="p-4 rounded-sm border border-white/10 bg-black/20 text-center">
                        <Trophy className="h-6 w-6 text-indigo-500 mx-auto mb-2" />
                        <div className="text-2xl font-black text-white">3</div>
                        <div className="text-[10px] uppercase tracking-widest text-white/40">Wins</div>
                    </div>
                </div>

                <div className="mt-8">
                    <button className="w-full h-12 inline-flex items-center justify-center rounded-sm text-sm font-bold uppercase tracking-widest bg-white text-black hover:bg-white/90 transition-colors">
                        Enter Race Hub
                    </button>
                </div>
            </CardContent>
        </Card>
    );
}
