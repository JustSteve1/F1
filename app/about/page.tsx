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
                <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl font-medium leading-[0.9] tracking-tight mb-24 md:mb-32">
                    Sport was never meant to be <span className="text-white/40">watched.</span><br />
                    It was meant to be <span className="italic">lived.</span>
                </h1>

                {/* Narrative Flow */}
                <div className="space-y-24 md:space-y-32 text-lg md:text-xl leading-relaxed text-white/80 font-light">

                    <p>
                        For decades, fans have sat behind the screen — watching decisions unfold, feeling the tension, imagining what they would do differently. But the screen was always a barrier. You could see everything. You could influence nothing.
                    </p>

                    <div className="pl-6 border-l-2 border-white/20">
                        <p className="font-serif text-3xl md:text-4xl text-white">
                            That era is ending.
                        </p>
                    </div>

                    <p>
                        A new layer of sport is emerging. One where every lap, every input, every moment of intent becomes something you can explore. Not as a spectator, but as a participant. Not as a viewer, but as part of the system itself.
                    </p>

                    <div className="space-y-8">
                        <p>
                            Because sport is not just motion.<br />
                            It’s intent, expressed through action.
                        </p>
                        <ul className="space-y-4 text-white/60">
                            <li className="flex items-center gap-4">
                                <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                                The braking point chosen under pressure.
                            </li>
                            <li className="flex items-center gap-4">
                                <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                                The line held when everything is on the limit.
                            </li>
                            <li className="flex items-center gap-4">
                                <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full" />
                                The difference between hesitation and commitment — measured in thousandths of a second.
                            </li>
                        </ul>
                    </div>

                    <div className="pl-6 border-l-2 border-indigo-500/50">
                        <p className="font-serif text-2xl md:text-3xl italic text-white/90">
                            These moments have always existed. Now, they’re visible.
                        </p>
                    </div>

                    <p>
                        We’ve built a platform that allows you to step inside performance — to move beyond watching outcomes and into understanding decisions. To compare, explore, and interact with the invisible structure beneath the sport you love.
                    </p>

                    <div className="text-center w-full py-12">
                        <p className="font-serif text-4xl md:text-5xl leading-tight">
                            You don’t just see what happened.<br />
                            <span className="text-indigo-400">You see why.</span>
                        </p>
                    </div>

                    <p>
                        And when you can see intent, everything changes.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 border-t border-b border-white/10 py-12">
                        <div className="font-mono text-xs uppercase tracking-widest text-white/40">The Future of Sport</div>
                        <div className="space-y-2 font-serif text-2xl">
                            <div className="text-white/40">Is not passive.</div>
                            <div className="text-white">It’s interactive.</div>
                            <div className="text-white">It’s measurable.</div>
                            <div className="text-indigo-400">It’s personal.</div>
                        </div>
                    </div>

                    <p>
                        This is where fans become participants.<br />
                        Where curiosity becomes capability.<br />
                        Where the distance between watching and doing disappears.
                    </p>

                    <div className="pt-24 md:pt-32">
                        <p className="font-serif text-xl md:text-2xl text-white/50 mb-4">
                            The screen was the first interface.
                        </p>
                        <p className="font-serif text-5xl md:text-7xl text-white">
                            This is the next.
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
