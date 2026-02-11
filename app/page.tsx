"use client";

import React, { useMemo, useState } from "react";

export default function WizardPage() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav = useMemo(
    () => [
      { label: "Sci-Fi", href: "/sci-fi" },
      { label: "Features", href: "/features" },
      { label: "Idea Factory", href: "/factory" },
      { label: "Pitwall", href: "/pitwall" },
      { label: "Frontier Films", href: "/frontier-films" },
      { label: "Work", href: "/work" },
      { label: "Docu-Style", href: "/work/docu-style" },
      { label: "Cinematic Spots", href: "/work/cinematic-spots" },
      { label: "Partners", href: "/work/partners" },
      { label: "About", href: "/about" },
      { label: "Press", href: "/press" },
      // The live page links out to wizard.inc for “Wizard”
      { label: "Wizard", href: "https://www.wizard.inc/", external: true },
      { label: "Work With Us", href: "/wizard" },
    ],
    []
  );

  const roles = useMemo(
    () => [
      {
        title: "Video Engine / Systems Engineer",
        blurb: "Forges the timeline from raw light and code...",
        href: "#",
      },
      {
        title: "Applied AI Engineer/Researcher",
        blurb: "Teaches the spells that write themselves...",
        href: "#",
      },
      {
        title: "Desktop Application Engineer",
        blurb: "Builds the tower every wizard calls home...",
        href: "#",
      },
      {
        title: "Media & Color Science Engineers",
        blurb: "Sees colors mortals can only dream of...",
        href: "#",
      },
      {
        title: "GPU / Accelerated Engineer",
        blurb: "Makes the CUDA magic happen...",
        href: "#",
      },
    ],
    []
  );

  // The live site uses a big ASCII block; keeping a smaller excerpt here.
  // Replace ASCII with the full block if you want 1:1.
  const ASCII = String.raw`
                                                                  .,,,,,
                                                              .,,,,.... ...
                                                           ..........       ..
                                                          .,,,.        .    ....
                                                         ..,......     .       ..
                                                        ..,,,.,.       .
                                                      ..,....,,.... 
                                                      ..,,,,,...... 
  `;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Top nav */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/70 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <a
            href="/"
            className="text-sm tracking-wide text-white/90 hover:text-white"
            aria-label="Story home"
          >
            Story
          </a>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-4 md:flex">
            {nav.map((item) => (
              <a
                key={item.label}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noreferrer" : undefined}
                className="text-xs text-white/70 hover:text-white"
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* Mobile toggle */}
          <button
            className="md:hidden rounded-md border border-white/15 px-3 py-1 text-xs text-white/80 hover:text-white"
            onClick={() => setMobileOpen((v) => !v)}
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
          >
            Menu
          </button>
        </div>

        {/* Mobile nav */}
        {mobileOpen && (
          <div id="mobile-nav" className="md:hidden border-t border-white/10">
            <div className="mx-auto max-w-5xl px-4 py-3">
              <div className="grid grid-cols-2 gap-2">
                {nav.map((item) => (
                  <a
                    key={item.label}
                    href={item.href}
                    target={item.external ? "_blank" : undefined}
                    rel={item.external ? "noreferrer" : undefined}
                    className="rounded-md border border-white/10 px-3 py-2 text-xs text-white/75 hover:text-white"
                    onClick={() => setMobileOpen(false)}
                  >
                    {item.label}
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main */}
      <main className="mx-auto max-w-5xl px-4 py-12 md:py-16">
        <h1 className="text-3xl font-light leading-tight tracking-tight md:text-5xl">
          Build a new standard for film &amp; video... that&apos;s not
          AI&nbsp;slop.
        </h1>

        <p className="mt-4 text-base text-white/70 md:text-lg">
          At a film studio, making movies.
        </p>

        <div className="mt-8">
          <a
            href="#"
            className="inline-flex items-center gap-2 text-sm text-white/80 hover:text-white"
          >
            <span className="underline underline-offset-4">
              General application here
            </span>
            <span aria-hidden>→</span>
          </a>
        </div>

        {/* Roles */}
        <section className="mt-8">
          <div className="grid gap-3 md:grid-cols-2">
            {roles.map((r) => (
              <a
                key={r.title}
                href={r.href}
                className="group rounded-xl border border-white/10 bg-white/0 p-4 hover:border-white/25"
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="text-sm font-medium text-white/90 group-hover:text-white">
                    {r.title}
                  </h3>
                  <span className="text-white/40 group-hover:text-white/70">
                    →
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-white/60">
                  {r.blurb}
                </p>
              </a>
            ))}
          </div>
        </section>

        {/* ASCII art */}
        <section className="mt-10">
          <pre className="overflow-x-auto rounded-xl border border-white/10 bg-white/0 p-4 text-[10px] leading-4 text-white/70 md:text-xs">
            {ASCII}
          </pre>
        </section>

        {/* Footer line */}
        <footer className="mt-10 text-xs tracking-wide text-white/60">
          SAN FRANCISCO, CA — STORY INSPIRES SCIENCE, SCIENCE MAKES STORY REAL.
        </footer>
      </main>
    </div>
  );
}
