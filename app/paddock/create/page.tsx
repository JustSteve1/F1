"use client";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { ArrowLeft, Save, Sparkles, Image as ImageIcon, Plus } from "lucide-react";
import Link from "next/link";
import { useState, useEffect } from "react";
import { Article } from "../paddock-data";
import { cn } from "@/lib/utils";

export default function CreatorStudio() {
    const [isPublishing, setIsPublishing] = useState(false);

    // Form State
    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [excerpt, setExcerpt] = useState("");
    const [author, setAuthor] = useState("");
    const [visualUrl, setVisualUrl] = useState("");
    const [visualType, setVisualType] = useState<'image' | 'svg' | 'video'>('image');

    // Auto-generated State
    const [id, setId] = useState("");
    const [date, setDate] = useState("");

    // Initialize Auto-generated fields
    useEffect(() => {
        // Simple random ID for MVP
        setId(Math.random().toString(36).substring(2, 9));

        // Current date formatted like "Feb 16, 2026"
        const now = new Date();
        setDate(now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }));
    }, []);

    // Smart Excerpt Generator
    const generateExcerpt = () => {
        if (!content) return;
        // Take first 150 chars or first paragraph
        const generated = content.substring(0, 150) + "...";
        setExcerpt(generated);
    };

    const handlePublish = () => {
        if (!title || !content || !author) {
            alert("Please fill in Title, Content, and Author.");
            return;
        }

        setIsPublishing(true);

        const newArticle: Article = {
            id,
            title,
            content,
            excerpt,
            author,
            date,
            readTime: "5 min read", // Mock calc
            imageUrl: visualUrl || "https://images.unsplash.com/photo-1533630654593-b2af8d313201?q=80&w=2600&auto=format&fit=crop",
            category: "Community",
            tags: ["New"],
            visualType,
            cta: "Subscribe"
        };

        console.log("Submitting New Article:", newArticle);

        // Mock API call
        setTimeout(() => {
            setIsPublishing(false);
            alert(`Story "${title}" Published Successfully! (Check Console for Data object)`);
            // Reset form
            setTitle("");
            setContent("");
            setExcerpt("");
        }, 1200);
    };

    return (
        <DashboardShell>
            <div className="min-h-screen bg-black text-white font-sans">

                {/* Header */}
                <div className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 bg-black/90 backdrop-blur-md border-b border-white/5">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/frontend/userpaddock"
                            className="flex items-center gap-2 text-white/50 hover:text-white transition-colors text-sm"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Exit</span>
                        </Link>
                        <div className="h-6 w-px bg-white/10" />
                        <h1 className="text-sm font-bold uppercase tracking-widest text-white/80">Creator Studio</h1>
                        <span className="text-xs text-white/20 font-mono">ID: {id}</span>
                    </div>

                    <button
                        onClick={handlePublish}
                        disabled={isPublishing}
                        className="flex items-center gap-2 bg-white text-black px-6 py-2 rounded-full text-sm font-bold hover:bg-white/90 transition-all disabled:opacity-50"
                    >
                        {isPublishing ? "Publishing..." : (
                            <>
                                <Save className="w-4 h-4" />
                                <span>Publish Story</span>
                            </>
                        )}
                    </button>
                </div>

                <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 p-8 lg:p-12">

                    {/* Main Editor Column */}
                    <div className="lg:col-span-8 flex flex-col gap-8">
                        {/* Title */}
                        <div className="group">
                            <label className="block text-xs uppercase tracking-widest text-white/30 mb-2 font-bold group-focus-within:text-red-500 transition-colors">Title</label>
                            <input
                                type="text"
                                placeholder="Enter your headline..."
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                className="w-full bg-transparent border-b border-white/10 py-2 text-4xl md:text-5xl font-serif font-bold text-white placeholder:text-white/10 focus:outline-none focus:border-red-500 transition-colors"
                            />
                        </div>

                        {/* Author */}
                        <div className="group">
                            <label className="block text-xs uppercase tracking-widest text-white/30 mb-2 font-bold group-focus-within:text-red-500 transition-colors">Author</label>
                            <input
                                type="text"
                                placeholder="Who is writing this?"
                                value={author}
                                onChange={(e) => setAuthor(e.target.value)}
                                className="w-full bg-transparent border-b border-white/10 py-2 text-xl font-serif text-white placeholder:text-white/10 focus:outline-none focus:border-red-500 transition-colors"
                            />
                        </div>

                        {/* Visuals */}
                        <div className="group bg-white/5 rounded-xl p-6 border border-white/5 focus-within:border-white/20 transition-colors">
                            <div className="flex items-center justify-between mb-4">
                                <label className="flex items-center gap-2 text-xs uppercase tracking-widest text-white/50 font-bold">
                                    <ImageIcon className="w-4 h-4" />
                                    Visual Media
                                </label>
                                <div className="flex gap-2">
                                    {(['image', 'svg', 'video'] as const).map(type => (
                                        <button
                                            key={type}
                                            onClick={() => setVisualType(type)}
                                            className={cn(
                                                "text-[10px] uppercase font-bold px-2 py-1 rounded-sm border transition-all",
                                                visualType === type
                                                    ? "bg-white text-black border-white"
                                                    : "bg-transparent text-white/40 border-white/10 hover:border-white/30"
                                            )}
                                        >
                                            {type}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <input
                                type="text"
                                placeholder={visualType === 'svg' ? "Paste SVG code here..." : "Paste Image URL..."}
                                value={visualUrl}
                                onChange={(e) => setVisualUrl(e.target.value)}
                                className="w-full bg-black/20 rounded-md border border-white/5 p-3 text-sm font-mono text-white/80 placeholder:text-white/10 focus:outline-none focus:border-white/20 transition-colors"
                            />
                            {visualUrl && visualType === 'image' && (
                                <div className="mt-4 rounded-lg overflow-hidden border border-white/10 aspect-video relative">
                                    <img src={visualUrl} alt="Preview" className="w-full h-full object-cover" />
                                </div>
                            )}
                        </div>

                        {/* Content */}
                        <div className="group flex-1">
                            <label className="block text-xs uppercase tracking-widest text-white/30 mb-4 font-bold">Story Content</label>
                            <textarea
                                placeholder="Tell your story..."
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                className="w-full min-h-[500px] bg-transparent border-none outline-none text-lg leading-relaxed text-white/80 placeholder:text-white/10 resize-none font-serif"
                            />
                        </div>
                    </div>

                    {/* Sidebar / Meta Column */}
                    <div className="lg:col-span-4 flex flex-col gap-6">

                        {/* Meta Card */}
                        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                            <h3 className="text-xs font-mono uppercase tracking-widest text-white/40 mb-6 font-bold">Logistics</h3>

                            <div className="grid grid-cols-2 gap-6 mb-6">
                                <div>
                                    <label className="block text-[10px] uppercase tracking-wider text-white/30 mb-1">ID</label>
                                    <div className="text-sm font-mono text-white/60">{id}</div>
                                </div>
                                <div>
                                    <label className="block text-[10px] uppercase tracking-wider text-white/30 mb-1">Date</label>
                                    <div className="text-sm font-mono text-white/60">{date}</div>
                                </div>
                            </div>
                        </div>

                        {/* Excerpt Card */}
                        <div className="bg-white/5 border border-white/10 rounded-xl p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-xs font-mono uppercase tracking-widest text-white/40 font-bold">Excerpt</h3>
                                <button
                                    onClick={generateExcerpt}
                                    className="text-[10px] flex items-center gap-1 text-red-400 hover:text-red-300 transition-colors uppercase font-bold tracking-wider"
                                >
                                    <Sparkles className="w-3 h-3" />
                                    Generate
                                </button>
                            </div>
                            <textarea
                                value={excerpt}
                                onChange={(e) => setExcerpt(e.target.value)}
                                placeholder="Short description for the feed..."
                                className="w-full h-32 bg-black/20 rounded-md border border-white/5 p-3 text-sm text-white/70 placeholder:text-white/10 focus:outline-none focus:border-white/20 transition-colors resize-none"
                            />
                        </div>

                        {/* CTA Placeholder */}
                        <div className="bg-gradient-to-br from-indigo-900/20 to-black border border-white/10 rounded-xl p-6 opacity-60">
                            <div className="flex items-center gap-2 mb-2 text-indigo-400">
                                <Plus className="w-4 h-4" />
                                <span className="text-xs font-bold uppercase tracking-widest">Call to Action</span>
                            </div>
                            <p className="text-xs text-white/40">
                                Future component: Select a newsletter signup or product link to embed.
                            </p>
                        </div>

                    </div>

                </div>

            </div>
        </DashboardShell>
    );
}
