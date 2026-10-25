"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { LiveTimingBoard } from "@/front-end/live/LiveTimingBoard";

export default function LiveTimingPage() {
  return (
    <DashboardShell>
      <LiveTimingBoard />
    </DashboardShell>
  );
}
