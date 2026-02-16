import { DashboardShell } from "@/components/layout/DashboardShell";
import { ARTICLES } from "@/app/paddock/paddock-data";
import { ArrowLeft, Clock, Calendar, Share, Bookmark } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

// For SSG in Next.js 13+, we can adhere to simple params handling
export const dynamicParams = true;

interface ArticlePageProps {
    params: Promise<{ id: string }>;
}

export default async function ArticlePage({ params }: ArticlePageProps) {
    // Await params for Next 15+ compatibility
    const { id } = await params;
    const article = ARTICLES.find((a) => a.id === id);

    if (!article) {
        notFound();
    }

    return (
        <DashboardShell>
            <div className="min-h-screen bg-black text-white font-serif">

                {/* Navigation Bar */}
                <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-4 bg-black/90 backdrop-blur-md border-b border-white/5">
                    <Link
                        href="/frontend/userpaddock"
                        className="flex items-center gap-2 text-white/50 hover:text-white transition-colors text-sm font-sans font-medium"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        <span>Paddock</span>
                    </Link>

                    <div className="flex items-center gap-4 text-white/50">
                        <button className="hover:text-white transition-colors">
                            <Bookmark className="w-5 h-5" />
                        </button>
                        <button className="hover:text-white transition-colors">
                            <Share className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Article Content */}
                <article className="max-w-3xl mx-auto px-6 py-10 md:py-16">

                    {/* Header */}
                    <header className="mb-10 text-center">
                        <div className="flex items-center justify-center gap-2 text-xs text-red-500 font-mono uppercase tracking-widest font-bold mb-4">
                            {article.category}
                        </div>

                        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6 text-white">
                            {article.title}
                        </h1>

                        <p className="text-xl md:text-2xl text-white/60 leading-relaxed mb-8 font-light italic">
                            {article.excerpt}
                        </p>

                        <div className="flex items-center justify-center gap-6 text-sm text-white/40 font-sans border-t border-b border-white/10 py-6">
                            <div className="text-left">
                                <div className="font-bold text-white mb-0.5">{article.author}</div>
                                <div className="text-xs text-red-500 uppercase tracking-wider font-bold">Author</div>
                            </div>
                            <div className="h-8 w-px bg-white/10" />
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                <span>{article.date}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                <span>{article.readTime}</span>
                            </div>
                        </div>
                    </header>

                    {/* Hero Image */}
                    <figure className="mb-12 rounded-xl overflow-hidden aspect-[16/9] relative">
                        <div
                            className="absolute inset-0 bg-cover bg-center"
                            style={{ backgroundImage: `url(${article.imageUrl})` }}
                        />
                    </figure>

                    {/* Body */}
                    <div
                        className="prose prose-invert prose-lg md:prose-xl max-w-none prose-headings:font-serif prose-p:font-serif prose-p:leading-loose text-white/80"
                        dangerouslySetInnerHTML={{ __html: article.content }}
                    />

                    {/* Tags */}
                    <div className="mt-16 pt-8 border-t border-white/10 flex flex-wrap gap-2">
                        {article.tags.map(tag => (
                            <span key={tag} className="px-3 py-1 bg-white/5 rounded-full text-xs font-sans text-white/60 hover:bg-white/10 transition-colors cursor-default">
                                #{tag}
                            </span>
                        ))}
                    </div>

                </article>

            </div>
        </DashboardShell>
    );
}
