"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { LiveTimingBoard } from "@/front-end/live/LiveTimingBoard";

export default function UserPitwallPage() {
    return (
        <DashboardShell>
            <LiveTimingBoard />
        </DashboardShell>
    );
}
