import Link from "next/link";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import { ExternalLink } from "lucide-react";

const KEY_LINKS = [
  {
    label: "Kaggle — Formula One All Laps & Telemetry",
    href: "https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2",
    note: "Public live lap and 2 Hz telemetry export for the full season (listing 9485317).",
  },
  {
    label: "GitHub — JustSteve1/F1",
    href: "https://github.com/JustSteve1/F1",
    note: "Source repository for the Live F1 Data Sync pipeline and API.",
  },
] as const;

export default function OverviewPage() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-white selection:text-black">
      <Header />

      <main className="mx-auto max-w-3xl px-6 pt-28 pb-24">
        {/* Confluence-style page header */}
        <div className="border-b border-white/10 pb-8 mb-10">
          <p className="text-xs font-mono tracking-widest text-white/40 uppercase mb-3">
            Interval.ai / Documentation
          </p>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-white">
              Live F1 Data Sync
            </h1>
            <span className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-400/30 bg-emerald-400/10 px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Live
            </span>
            <span className="inline-flex items-center rounded-sm border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] font-mono uppercase tracking-wider text-white/60">
              Sub-100ms API
            </span>
          </div>
          <p className="text-sm text-white/45 font-mono">
            Last updated: 8 Aug 2026
          </p>
        </div>

        {/* Info panel */}
        <aside className="mb-12 rounded-sm border border-white/10 bg-white/[0.03] p-5">
          <h2 className="text-xs font-mono uppercase tracking-widest text-white/40 mb-3">
            Summary
          </h2>
          <p className="text-sm text-white/75 leading-relaxed">
            API that syncs live Formula 1 data with ~0.1s latency. Provides session
            timing and race state for applications that consume real-time motorsport
            feeds.
          </p>
        </aside>

        {/* Body — confluence update tone */}
        <article className="space-y-10 text-[15px] leading-relaxed text-white/75">
          <section>
            <h2 className="text-lg font-semibold text-white mb-3 border-b border-white/10 pb-2">
              Overview
            </h2>
            <p className="mb-3">
              Live F1 Data Sync is the data layer behind Interval.ai. It ingests
              Formula 1 session feeds, normalises timing and race state, and exposes
              them over a REST API with typical response latency around 0.1 seconds.
            </p>
            <p>
              Downstream clients (Interval.ai product surfaces, internal tools, and
              research exports) consume the same sync path. This page is the project
              overview for that API and its related artefacts.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white mb-3 border-b border-white/10 pb-2">
              What it provides
            </h2>
            <ul className="list-disc pl-5 space-y-2 marker:text-white/30">
              <li>Live session timing and race state sync</li>
              <li>Sub-100ms API responses under normal load (~0.1s typical)</li>
              <li>Structured exports for analysis (see Key Links → Kaggle)</li>
              <li>Shared source of truth for Interval.ai pitwall experiences</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white mb-3 border-b border-white/10 pb-2">
              Current scope
            </h2>
            <p className="mb-3">
              Active sync covers Formula 1 session data used by the Interval.ai
              front-end. Dataset snapshots are published periodically for offline
              review and model work.
            </p>
            <p>
              The live Formula One all-laps dataset is published on Kaggle
              (link below). Additional sessions follow the same export path as they
              are imported.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white mb-3 border-b border-white/10 pb-2">
              Key Links
            </h2>
            <div className="rounded-sm border border-white/10 divide-y divide-white/10">
              {KEY_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target={link.href.startsWith("http") ? "_blank" : undefined}
                  rel={link.href.startsWith("http") ? "noopener noreferrer" : undefined}
                  className="flex items-start justify-between gap-4 p-4 hover:bg-white/[0.04] transition-colors group"
                >
                  <div>
                    <p className="text-sm font-medium text-white group-hover:underline underline-offset-2">
                      {link.label}
                    </p>
                    <p className="mt-1 text-xs text-white/45 leading-relaxed">
                      {link.note}
                    </p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-white/30 group-hover:text-white/70 shrink-0 mt-0.5" />
                </a>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white mb-3 border-b border-white/10 pb-2">
              Notes
            </h2>
            <ul className="list-disc pl-5 space-y-2 marker:text-white/30">
              <li>
                Latency figure (~0.1s) is typical observed API response time, not a
                contractual SLA.
              </li>
              <li>
                Kaggle exports are point-in-time snapshots; live API data may be
                newer.
              </li>
              <li>
                For product access, use{" "}
                <Link href="/signup" className="text-white underline underline-offset-2 hover:text-white/80">
                  Sign up
                </Link>{" "}
                or{" "}
                <Link href="/login" className="text-white underline underline-offset-2 hover:text-white/80">
                  Sign in
                </Link>
                .
              </li>
            </ul>
          </section>
        </article>
      </main>

      <Footer />
    </div>
  );
}
