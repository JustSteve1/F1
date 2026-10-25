"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { SpeedMap } from "@/front-end/live/SpeedMap";

export default function SpeedMapPage() {
  return (
    <DashboardShell>
      <SpeedMap />
    </DashboardShell>
  );
}
