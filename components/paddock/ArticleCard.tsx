import { Calendar, Clock, ArrowRight } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface Article {
    id: string;
    title: string;
    excerpt: string;
    author: string;
    date: string;
    readTime: string;
    imageUrl: string;
    category: string;
}

interface ArticleCardProps {
    article: Article;
    variant?: "featured" | "standard" | "minimal";
    className?: string;
}

export function ArticleCard({ article, variant = "standard", className }: ArticleCardProps) {
    if (variant === "minimal") {
        return (
            <Link
                href={`/frontend/userpaddock/${article.id}`}
                className={cn("group flex gap-4 items-start p-4 hover:bg-white/5 transition-colors rounded-lg", className)}
            >
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-xs text-white/40 mb-1 font-mono uppercase tracking-wider">
                        <span className="text-red-500 font-bold">{article.category}</span>
                        <span>•</span>
                        <span>{article.date}</span>
                    </div>
                    <h3 className="text-lg font-serif font-medium text-white group-hover:text-red-500 transition-colors line-clamp-2 leading-snug">
                        {article.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-2 text-xs text-white/40">
                        <span>{article.author}</span>
                    </div>
                </div>
            </Link>
        );
    }

    if (variant === "featured") {
        return (
            <Link
                href={`/frontend/userpaddock/${article.id}`}
                className={cn("group relative block aspect-[16/9] w-full overflow-hidden rounded-xl", className)}
            >
                {/* Background Image */}
                <div
                    className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
                    style={{ backgroundImage: `url(${article.imageUrl})` }}
                />

                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent opacity-90" />

                {/* Content */}
                <div className="absolute bottom-0 left-0 p-6 md:p-8 max-w-3xl">
                    <div className="flex items-center gap-3 text-xs md:text-sm text-white/60 mb-3 font-mono uppercase tracking-wider">
                        <span className="bg-red-600 text-white px-2 py-0.5 rounded-sm font-bold">{article.category}</span>
                        <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            <span>{article.date}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{article.readTime}</span>
                        </div>
                    </div>

                    <h2 className="text-3xl md:text-4xl lg:text-5xl font-serif font-bold text-white mb-3 leading-tight group-hover:underline decoration-red-500 decoration-2 underline-offset-4">
                        {article.title}
                    </h2>

                    <p className="text-white/70 line-clamp-2 md:text-lg max-w-2xl mb-4 font-serif">
                        {article.excerpt}
                    </p>

                    <div className="flex items-center gap-2 text-sm text-white/50">
                        <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-[10px] font-bold">
                            {article.author.charAt(0)}
                        </div>
                        <span>{article.author}</span>
                    </div>
                </div>
            </Link>
        );
    }

    // Standard Variant
    return (
        <Link
            href={`/frontend/userpaddock/${article.id}`}
            className={cn("group flex flex-col gap-3 rounded-lg overflow-hidden", className)}
        >
            <div className="relative aspect-[3/2] overflow-hidden rounded-lg bg-white/5">
                <div
                    className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-105"
                    style={{ backgroundImage: `url(${article.imageUrl})` }}
                />
            </div>

            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs text-white/40 font-mono uppercase tracking-wider">
                    <span className="text-red-500 font-bold">{article.category}</span>
                    <span>•</span>
                    <span>{article.date}</span>
                </div>

                <h3 className="text-xl font-serif font-bold text-white leading-tight group-hover:text-red-500 transition-colors">
                    {article.title}
                </h3>

                <p className="text-sm text-white/50 line-clamp-2 font-serif leading-relaxed">
                    {article.excerpt}
                </p>

                <div className="flex items-center gap-2 mt-auto pt-2 text-xs text-white/30">
                    <span>by {article.author}</span>
                </div>
            </div>
        </Link>
    );
}
