"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-black text-white font-sans selection:bg-white selection:text-black overflow-x-hidden">
            {/* Ambient Background Glow */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/10 rounded-full blur-[120px]" />
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-indigo-900/10 rounded-full blur-[120px]" />
            </div>

            {/* Navigation (Minimalist) */}
            <nav className="fixed top-0 left-0 w-full p-8 z-50 mix-blend-difference">
                <Link
                    href="/"
                    className="group flex items-center gap-2 text-sm font-mono text-white/50 hover:text-white transition-colors"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    <span>home</span> <span className="text-white/20">|</span> <span>about</span>
                </Link>
            </nav>

            {/* Main Content Column */}
            <main className="relative z-10 max-w-2xl mx-auto px-6 py-32 md:py-48 flex flex-col items-start">

                {/* Hero Statement */}
                <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl font-medium leading-[0.9] tracking-tight mb-12 md:mb-16">
                    You took the call.<br />
                    You owned the <span className="text-white/40">outcome.</span>
                </h1>

                <p className="font-serif text-2xl md:text-3xl lg:text-4xl text-white/80 mb-24 md:mb-32 max-w-3xl leading-tight">
                    Sport was never meant to be watched.<br />
                    It was meant to be <span className="italic text-indigo-400">played.</span>
                </p>

                {/* Narrative Flow */}
                <div className="space-y-16 md:space-y-24 text-lg md:text-xl leading-relaxed text-white/80 font-light max-w-2xl">

                    <p>
                        For decades the screen gave you everything — the tension, the data, the moment — and then took the only thing that mattered away from you. The decision. That always belonged to the team.
                    </p>

                    <div className="pl-6 border-l-2 border-white/20">
                        <p className="font-serif text-3xl md:text-4xl text-white">
                            Not anymore.
                        </p>
                    </div>

                    <p>
                        Every lap has micro-decision points buried inside it. A pit window opened and closed. A tire pushed one lap too far, or pulled one lap too early. A gap on the timing screen that told the whole story — if you knew how to read it.
                    </p>

                    <p>
                        You watched these decisions happen. You saw the outcomes play out. What we built is the space between the two — where you stand at the pitwall with the same data at your fingertips, in the same moment, and make the call yourself.
                    </p>

                    <div className="space-y-8">
                        <p className="font-bold text-white text-2xl">
                            Not a simulation. Not fantasy. The real race, frozen at the moment of consequence.
                        </p>
                    </div>

                    <div className="text-left w-full py-8">
                        <p className="font-serif text-4xl md:text-5xl leading-tight text-white mb-4">
                            You decide.<br />
                            <span className="text-white/40">Then reality plays out.</span>
                        </p>
                    </div>

                    <p>
                        That gap — between your instinct and the truth — is where everything lives. It&apos;s where you learn how the fastest sport on earth actually thinks. Where data stops being numbers on a screen and becomes the difference between a championship and a footnote.
                    </p>

                    <div className="pt-24 md:pt-32 border-t border-white/10">
                        <p className="font-serif text-xl md:text-2xl text-white/50 mb-4">
                            This is not the future of watching sport.
                        </p>
                        <p className="font-serif text-5xl md:text-6xl text-indigo-400">
                            It&apos;s the end of watching it.
                        </p>
                    </div>

                </div>

                {/* Footer Signature */}
                <footer className="w-full mt-48 pt-12 border-t border-white/10 flex justify-between items-end">
                    <div className="text-xs font-mono text-white/30">
                        COPYRIGHT © 2026 INPLAY
                    </div>
                    <div className="text-xs font-mono text-white/30 text-right">
                        DESIGNED AT THE EDGE
                    </div>
                </footer>

            </main>
        </div>
    );
}
