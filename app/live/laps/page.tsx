"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { LiveLapsTable } from "@/front-end/live/LiveLapsTable";

export default function LiveLapsPage() {
  return (
    <DashboardShell>
      <LiveLapsTable />
    </DashboardShell>
  );
}
