"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { ArticleCard } from "@/components/paddock/ArticleCard";
import { PenTool } from "lucide-react";
import Link from "next/link";
import { ARTICLES } from "@/app/paddock/paddock-data";

export default function PaddockPage() {
    const featuredArticle = ARTICLES[0];
    const mainFeed = ARTICLES.slice(1, 3);
    const sidebarFeed = ARTICLES.slice(3);

    return (
        <DashboardShell>
            <div className="flex flex-col gap-6 p-6 md:p-10 max-w-[1600px] mx-auto">

                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-4xl md:text-5xl font-serif font-black tracking-tight text-white mb-2">
                            The Paddock
                        </h1>
                        <p className="text-white/60 font-serif text-lg">
                            Curated stories, technical analysis, and the pulse of the pitlane.
                        </p>
                    </div>

                    <Link
                        href="/paddock/create"
                        className="flex items-center gap-2 bg-white text-black px-5 py-2.5 rounded-full font-bold hover:bg-white/90 transition-all shadow-lg shadow-white/10"
                    >
                        <PenTool className="w-4 h-4" />
                        <span>Write a Story</span>
                    </Link>
                </div>

                {/* Featured Story (Hero) */}
                <section className="mb-0">
                    <ArticleCard article={featuredArticle} variant="featured" />
                </section>

                {/* Main Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">

                    {/* Main Feed Column */}
                    <div className="lg:col-span-8 flex flex-col gap-10">
                        <div className="flex items-center justify-between border-b border-white/10 pb-4">
                            <h2 className="text-xl font-mono uppercase tracking-widest font-bold text-white">Latest Stories</h2>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {mainFeed.map(article => (
                                <ArticleCard key={article.id} article={article} variant="standard" />
                            ))}
                        </div>

                        {/* More stories placeholder */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            {/* Reusing mock data to fill space visually if needed */}
                        </div>
                    </div>

                    {/* Sidebar / Trending Column */}
                    <div className="lg:col-span-4 flex flex-col gap-8">
                        <div className="bg-white/5 rounded-xl p-6 border border-white/10">
                            <h3 className="text-sm font-mono uppercase tracking-widest text-white/50 mb-6 font-bold">In Brief</h3>
                            <div className="flex flex-col gap-2">
                                {sidebarFeed.map(article => (
                                    <div key={article.id} className="border-b border-white/5 last:border-0 pb-4 last:pb-0">
                                        <ArticleCard article={article} variant="minimal" className="p-0 hover:bg-transparent" />
                                    </div>
                                ))}
                                {/* Duplicate for visual length */}
                                <div className="border-b border-white/5 last:border-0 pb-4 last:pb-0">
                                    <ArticleCard article={ARTICLES[2]} variant="minimal" className="p-0 hover:bg-transparent" />
                                </div>
                            </div>
                        </div>

                        <div className="bg-gradient-to-br from-red-900/20 to-black rounded-xl p-8 border border-white/10 text-center">
                            <h3 className="font-serif text-2xl mb-2 text-white">Join the Conversation</h3>
                            <p className="text-white/60 mb-6 text-sm">Submit your technical analysis or opinion piece to The Paddock.</p>
                            <Link href="/paddock/create" className="text-red-400 text-sm font-bold uppercase tracking-widest hover:text-red-300">
                                Start Writing →
                            </Link>
                        </div>
                    </div>

                </div>

            </div>
        </DashboardShell>
    );
}
