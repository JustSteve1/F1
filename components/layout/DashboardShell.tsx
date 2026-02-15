"use client";

import { Sidebar } from "./Sidebar";

export function DashboardShell({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex min-h-screen bg-black text-white">
            {/* Sidebar - Hidden on mobile, visible on desktop */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 p-4 md:p-8 overflow-y-auto">
                <div className="mx-auto max-w-7xl h-full flex flex-col justify-center">
                    {children}
                </div>
            </main>
        </div>
    );
}
