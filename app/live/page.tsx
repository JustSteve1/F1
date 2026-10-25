"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { LiveStatusStrip } from "@/front-end/live/LiveStatusStrip";
import { LiveTimingBoard } from "@/front-end/live/LiveTimingBoard";

export default function LiveTimingPage() {
  return (
    <DashboardShell>
      <LiveStatusStrip />
      <LiveTimingBoard />
    </DashboardShell>
  );
}
