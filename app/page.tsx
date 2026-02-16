import Image from "next/image";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import Link from "next/link";
import { ARTICLES } from "@/app/paddock/paddock-data";
import { ArrowUpRight } from "lucide-react";

// Force dynamic rendering to ensure random articles on every request
export const dynamic = 'force-dynamic';

export default function Home() {
  // Get 4 random articles
  const shuffled = [...ARTICLES].sort(() => 0.5 - Math.random());
  const selectedArticles = shuffled.slice(0, 4);

  // Map to specific slots for readability
  const [heroArticle, verticalArticle, smallArticle, wideArticle] = selectedArticles;

  return (
    <div className="min-h-screen bg-black text-white selection:bg-white selection:text-black">
      <Header />

      <main>
        {/* HERO SECTION */}
        <section className="relative h-screen w-full overflow-hidden">
          <Image
            src="/images/hero.png"
            alt="F1 Car on Track"
            fill
            className="object-cover object-center grayscale contrast-125"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black" />

          <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-4">
            <h1 className="text-[12vw] font-black leading-none tracking-tighter mix-blend-overlay opacity-90">
              SPEED
            </h1>
            <h1 className="text-[12vw] font-black leading-none tracking-tighter text-transparent stroke-white stroke-2 opacity-80 mt-[-2vw]">
              DEFINED
            </h1>
            <p className="mt-8 text-lg md:text-xl font-light tracking-widest uppercase text-white/80 max-w-lg">
              Precision. Power. Performance.
            </p>
          </div>

          <div className="absolute bottom-12 left-0 right-0 flex justify-center animate-bounce">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-8 h-8 text-white/50"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </div>
        </section>

        {/* CONTENT GRID */}
        <section className="mx-auto max-w-7xl px-4 py-24">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-[400px]">

            {/* Item 1: Large Feature (Hero Style) */}
            {heroArticle && (
              <Link
                href={`/frontend/userpaddock/${heroArticle.id}`}
                className="group relative col-span-1 md:col-span-2 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 block"
              >
                <Image
                  src={heroArticle.imageUrl}
                  alt={heroArticle.title}
                  fill
                  className="object-cover transition-transform duration-700 group-hover:scale-105 opacity-60 group-hover:opacity-40"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-90" />
                <div className="absolute bottom-0 left-0 p-8 w-full">
                  <div className="flex justify-between items-end">
                    <div>
                      <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-indigo-400">
                        <Link href="/frontend/userfactory" className="hover:text-white transition-colors border-b border-indigo-400/30 pb-0.5 hover:border-white">Latest</Link> News
                      </span>
                      <h3 className="text-3xl font-bold uppercase tracking-tight text-white group-hover:text-indigo-400 transition-colors">
                        {heroArticle.title}
                      </h3>
                      <p className="mt-2 line-clamp-2 text-white/60 max-w-lg">
                        {heroArticle.excerpt}
                      </p>
                    </div>
                    <ArrowUpRight className="hidden md:block w-6 h-6 text-white/30 group-hover:text-white transition-colors" />
                  </div>
                </div>
              </Link>
            )}

            {/* Item 2: Vertical Highlight */}
            {verticalArticle && (
              <Link
                href={`/frontend/userpaddock/${verticalArticle.id}`}
                className="group relative col-span-1 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 block"
              >
                <Image
                  src={verticalArticle.imageUrl}
                  alt={verticalArticle.title}
                  fill
                  className="object-cover transition-transform duration-700 group-hover:scale-110 opacity-50"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-transparent to-black/80" />
                <div className="absolute inset-0 flex flex-col justify-between p-8">
                  <div>
                    <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-emerald-400">{verticalArticle.category}</span>
                    <h3 className="text-4xl font-black uppercase tracking-tighter text-white leading-tight">
                      {verticalArticle.title}
                    </h3>
                  </div>
                  <div className="space-y-4">
                    <p className="text-white/70 font-serif italic text-lg leading-relaxed line-clamp-6">
                      &quot;{verticalArticle.excerpt}&quot;
                    </p>
                    <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 pt-4 border-t border-white/10">
                      <span>READ FULL STORY</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </div>
                  </div>
                </div>
              </Link>
            )}

            {/* Item 3: Small/Media */}
            {smallArticle && (
              <Link
                href={`/frontend/userpaddock/${smallArticle.id}`}
                className="group relative col-span-1 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 flex items-center justify-center text-center p-6"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="relative z-10">
                  <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-white/5 group-hover:scale-110 group-hover:border-white/40 transition-all">
                    <span className="text-2xl">🏎️</span>
                  </div>
                  <span className="block text-xs font-bold uppercase tracking-widest text-white/40 mb-2">{smallArticle.category}</span>
                  <h3 className="text-xl font-bold uppercase tracking-wide text-white group-hover:text-red-500 transition-colors line-clamp-2">
                    {smallArticle.title}
                  </h3>
                  <p className="mt-4 text-xs font-mono text-white/30">
                    {smallArticle.readTime}
                  </p>
                </div>
              </Link>
            )}

            {/* Item 4: Wide/Quote Style */}
            {wideArticle && (
              <Link
                href={`/frontend/userpaddock/${wideArticle.id}`}
                className="group relative col-span-1 md:col-span-2 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 p-8 md:p-12 flex items-center"
              >
                <div className="absolute top-0 right-0 p-4 opacity-10">
                  <span className="text-9xl font-serif font-black">“</span>
                </div>
                <div className="relative z-10 max-w-2xl">
                  <blockquote className="text-2xl md:text-3xl font-light italic leading-relaxed text-white/80 group-hover:text-white transition-colors">
                    &quot;{wideArticle.excerpt}&quot;
                    <footer className="mt-6 flex items-center gap-3 text-sm font-bold uppercase not-italic text-white/50">
                      <span className="h-px w-8 bg-white/30"></span>
                      {wideArticle.author}
                    </footer>
                  </blockquote>
                </div>
              </Link>
            )}

          </div>
        </section>

        {/* FEATURE CARDS SECTION */}
        <section className="mx-auto max-w-7xl px-4 pb-24 border-t border-white/10 pt-24">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

            {/* Paddock Feature */}
            <Link href="/frontend/userpaddock" className="group block space-y-4 p-8 border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/30 transition-all duration-500 rounded-sm">
              <div className="h-12 w-12 flex items-center justify-center rounded-full bg-indigo-500/10 text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white mb-2">The Paddock</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-white/80 transition-colors">
                  <span className="text-indigo-400 font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2">The Pulse.</span>
                  Curated stories, technical deep-dives, and the narrative behind the numbers.
                </p>
              </div>
            </Link>

            {/* Pitwall Feature */}
            <Link href="/frontend/userpitwall" className="group block space-y-4 p-8 border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/30 transition-all duration-500 rounded-sm">
              <div className="h-12 w-12 flex items-center justify-center rounded-full bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white mb-2">The Pitwall</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-white/80 transition-colors">
                  <span className="text-emerald-400 font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2">The Data.</span>
                  Real-time telemetry, strategy analysis, and the view from the command center.
                </p>
              </div>
            </Link>

            {/* Factory Feature */}
            <Link href="/frontend/userfactory" className="group block space-y-4 p-8 border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/30 transition-all duration-500 rounded-sm">
              <div className="h-12 w-12 flex items-center justify-center rounded-full bg-red-500/10 text-red-400 group-hover:bg-red-500 group-hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.423 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.423 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.703.127 1.5.876 2.683 2.626 2.763 2.898.04.137-.059.279-.197.279h-.7a.75.75 0 01-.75-.75S16.142 5.6 9.875 5.25m6.656 7.625l-1.31-2.098c-.297-.476-.413-1.056-.32-1.623.196-1.19.866-2.27 1.838-2.955" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white mb-2">The Factory</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-white/80 transition-colors">
                  <span className="text-red-400 font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2">The Source.</span>
                  Development, upgrades, and the relentless pursuit of performance.
                </p>
              </div>
            </Link>

          </div>
        </section>

      </main>

      <Footer />
    </div >
  );
}
