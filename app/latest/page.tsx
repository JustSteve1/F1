import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import Link from "next/link";

// Mock Data
const articles = [
    {
        id: 1,
        title: "New Regulations for 2026: A Deep Dive",
        category: "Technical",
        date: "OCT 12, 2025",
        excerpt: "The FIA announces groundbreaking changes to the technical regulations, focusing on sustainability and closer racing. We analyze what this means for the teams.",
        image: "/images/hero.png", // Using hero as placeholder for now
    },
    {
        id: 2,
        title: "Leclerc's Masterclass in Monaco",
        category: "Race Report",
        date: "MAY 28, 2025",
        excerpt: "A home victory that was long overdue. Charles Leclerc dominates the streets of Monte Carlo in a display of pure precision and control.",
        image: "/images/hero.png",
    },
    {
        id: 3,
        title: "The Rise of Rookie Sensation Kimi Antonelli",
        category: "Feature",
        date: "SEP 15, 2025",
        excerpt: "From karting prodigy to F1 superstar? We track the rapid ascent of Mercedes' latest wunderkind.",
        image: "/images/hero.png",
    },
    {
        id: 4,
        title: "Red Bull's Powertrain Gamble",
        category: "Analysis",
        date: "AUG 03, 2025",
        excerpt: "As the 2026 deadline approaches, we look at the progress of Red Bull Powertrains and their partnership with Ford.",
        image: "/images/hero.png",
    },
    {
        id: 5,
        title: "Understanding the 2025 Aero Upgrades",
        category: "Tech Talk",
        date: "JUL 22, 2025",
        excerpt: "McLaren's latest floor update explained. How vortices are being managed under the new regulations.",
        image: "/images/hero.png",
    },
    {
        id: 6,
        title: "Sustainable Fuels: The Future of Speed",
        category: "Innovation",
        date: "JUN 10, 2025",
        excerpt: "F1 is pioneering 100% sustainable fuels. Here is the science behind the drop-in replacement that could save the internal combustion engine.",
        image: "/images/hero.png",
    }
];

export default function LatestPage() {
    return (
        <div className="min-h-screen bg-black text-white selection:bg-white selection:text-black">
            <Header />

            <main className="pt-24 pb-24 px-6">
                <div className="mx-auto max-w-7xl">
                    {/* Page Header */}
                    <header className="mb-16 border-b border-white/10 pb-8">
                        <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-white uppercase mb-4">
                            Latest <span className="text-white/30">Transmissions</span>
                        </h1>
                        <p className="text-white/60 max-w-2xl text-lg">
                            Breaking news, race reports, and technical analysis from the paddock.
                        </p>
                    </header>

                    {/* Content Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-12">
                        {articles.map((article) => (
                            <article key={article.id} className="group cursor-pointer">
                                {/* Image Container */}
                                <div className="relative aspect-video w-full overflow-hidden rounded-sm bg-white/5 mb-6 border border-white/10 group-hover:border-white/30 transition-colors">
                                    <div className="absolute inset-0 bg-white/5 group-hover:bg-white/10 transition-colors z-10" />
                                    {/* Placeholder for image - using a div for now if image fails, or the actual image component */}
                                    {/* <Image src={article.image} fill className="object-cover grayscale contrast-125 group-hover:scale-105 transition-transform duration-700" alt={article.title} /> */}
                                    <div className="absolute inset-0 flex items-center justify-center text-white/10 text-4xl font-black uppercase tracking-tighter">
                                        InPlay Image
                                    </div>
                                </div>

                                {/* Content */}
                                <div className="space-y-3">
                                    <div className="flex items-center gap-3 text-xs font-bold tracking-widest uppercase">
                                        <span className="text-indigo-400">{article.category}</span>
                                        <span className="text-white/30 md:block hidden">•</span>
                                        <span className="text-white/40">{article.date}</span>
                                    </div>

                                    <h2 className="text-2xl font-bold leading-tight uppercase tracking-tight group-hover:text-white/70 transition-colors">
                                        {article.title}
                                    </h2>

                                    <p className="text-white/50 text-sm leading-relaxed line-clamp-3">
                                        {article.excerpt}
                                    </p>

                                    <div className="pt-2">
                                        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-white border-b border-white/30 pb-0.5 group-hover:border-white transition-colors">
                                            Read Article
                                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
                                                <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                                            </svg>
                                        </span>
                                    </div>
                                </div>
                            </article>
                        ))}
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
