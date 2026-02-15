"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { PitwallDashboard } from "@/front-end/pitwall/PitwallDashboard";

export default function UserPitwallPage() {
    return (
        <DashboardShell>
            <PitwallDashboard />
        </DashboardShell>
    );
}
