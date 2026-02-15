import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MoveUpRight } from "lucide-react";

export function InfoTile() {
    return (
        <Card className="group relative overflow-hidden border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
            <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80" />
            <CardHeader className="relative z-10">
                <div className="flex justify-between items-start">
                    <div className="space-y-1">
                        <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-indigo-400">Latest News</span>
                        <CardTitle className="text-2xl font-black uppercase tracking-tighter text-white">Season 2026</CardTitle>
                    </div>
                    <MoveUpRight className="h-5 w-5 text-white/50 transition-transform group-hover:-translate-y-1 group-hover:translate-x-1" />
                </div>
            </CardHeader>
            <CardContent className="relative z-10">
                <p className="text-sm font-light text-white/80 leading-relaxed max-w-[90%]">
                    Get ready for the most exciting season yet with new regulations and driver lineups.
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                    <span className="inline-flex items-center rounded-sm border border-white/20 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white transition-colors hover:bg-white/10">
                        Regulations
                    </span>
                    <span className="inline-flex items-center rounded-sm border border-white/20 bg-white/5 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-white transition-colors hover:bg-white/10">
                        Drivers
                    </span>
                </div>
            </CardContent>
        </Card>
    );
}
