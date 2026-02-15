"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { FactoryDashboard } from "@/front-end/factory/FactoryDashboard";

export default function UserFactoryPage() {
    return (
        <DashboardShell>
            <FactoryDashboard />
        </DashboardShell>
    );
}
