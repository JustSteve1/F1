import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Gamepad2 } from "lucide-react";

export function SocialLoginTile() {
    return (
        <Card className="flex flex-col justify-between border border-white/10 bg-white/5 rounded-sm hover:border-white/30 transition-all duration-500">
            <CardHeader>
                <div className="flex items-center gap-4">
                    <div className="p-3 rounded-full border border-white/10 bg-white/5 text-white">
                        <Gamepad2 className="h-5 w-5" />
                    </div>
                    <div>
                        <CardTitle className="text-xl font-bold uppercase tracking-tight text-white">Gamertag</CardTitle>
                        <CardDescription className="text-xs uppercase tracking-widest text-white/50">Connect Accounts</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <button className="group flex w-full items-center justify-between rounded-sm border border-white/10 bg-white/5 p-4 hover:border-white/30 hover:bg-white/10 transition-all">
                    <span className="font-bold uppercase tracking-wide text-sm text-white">PlayStation</span>
                    <span className="text-xs uppercase tracking-widest text-white/40 group-hover:text-white transition-colors">Connect</span>
                </button>
                <button className="group flex w-full items-center justify-between rounded-sm border border-white/10 bg-white/5 p-4 hover:border-white/30 hover:bg-white/10 transition-all">
                    <span className="font-bold uppercase tracking-wide text-sm text-white">Xbox Live</span>
                    <span className="text-xs uppercase tracking-widest text-white/40 group-hover:text-white transition-colors">Connect</span>
                </button>
            </CardContent>
        </Card>
    );
}
