"use client";

import { AuthLoginTile } from "./AuthLoginTile";
import { SocialLoginTile } from "./SocialLoginTile";
import { InfoTile } from "./InfoTile";
import { Sidebar } from "../layout/Sidebar";

export function LoginGrid() {
    return (
        <div className="flex min-h-screen bg-black text-white">
            {/* Sidebar - Hidden on mobile, visible on desktop */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 p-4 md:p-8 overflow-y-auto">
                <div className="mx-auto max-w-7xl h-full flex flex-col justify-center">

                    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 md:gap-6 min-h-[600px]">

                        {/* Auth Tile - Main Feature */}
                        <div className="md:col-span-4 lg:col-span-4 row-span-2">
                            <AuthLoginTile />
                        </div>

                        {/* Info Tile - News / Updates */}
                        <div className="md:col-span-8 lg:col-span-5 row-span-1">
                            <InfoTile />
                        </div>

                        {/* Social Login Tile */}
                        <div className="md:col-span-8 lg:col-span-3 row-span-1">
                            <SocialLoginTile />
                        </div>

                        {/* Placeholder for future tiles to complete Bento grid effect */}
                        <div className="md:col-span-8 lg:col-span-8 row-span-1 bg-white/5 rounded-sm border border-white/10 border-dashed flex items-center justify-center min-h-[200px]">
                            <span className="text-white/20 text-xs font-bold uppercase tracking-widest">Future Widget Space</span>
                        </div>

                    </div>

                    <div className="mt-8 text-center text-sm text-muted-foreground opacity-20">
                        <p>Built with Next.js & Tailwind CSS</p>
                    </div>
                </div>
            </main>
        </div>
    );
}
