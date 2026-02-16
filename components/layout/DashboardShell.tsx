"use client";

import { Sidebar } from "./Sidebar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-screen overflow-hidden bg-black text-white">
            {/* Sidebar - Hidden on mobile, visible on desktop */}
            <aside className="hidden md:flex flex-col border-r border-white/10 bg-black">
                <Sidebar />
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto p-4 md:p-8 scrollbar-hide">
                <div className="mx-auto max-w-7xl">
                    {children}
                </div>
            </main>
        </div>
    );
}
