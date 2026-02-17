import Image from "next/image";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import Link from "next/link";
import { ARTICLES } from "@/app/paddock/paddock-data";
import { ArrowUpRight } from "lucide-react";
import StatsCounter from "@/components/ui/StatsCounter";

// Force dynamic rendering to ensure random articles on every request
export const dynamic = 'force-dynamic';

export default function Home() {
  // Get 4 random articles
  // const shuffled = [...ARTICLES].sort(() => 0.5 - Math.random());
  // const selectedArticles = shuffled.slice(0, 4);

  // Map to specific slots for readability
  // const [heroArticle, verticalArticle, smallArticle, wideArticle] = selectedArticles;

  return (
    <div className="min-h-screen bg-black text-white selection:bg-white selection:text-black">
      <Header />

      <main>
        {/* HERO SECTION */}
        <section className="relative min-h-screen w-full bg-black grid grid-cols-1 lg:grid-cols-2 overflow-hidden">

          {/* Left Content */}
          <div className="flex flex-col justify-center px-6 py-20 lg:pl-24 lg:pr-12 relative z-10 order-2 lg:order-1">
            <h1 className="text-[5vw] lg:text-[4.5vw] font-black leading-none tracking-tighter mb-2 whitespace-nowrap uppercase">
              <span className="bg-clip-text text-transparent bg-gradient-to-b from-white via-gray-300 to-gray-500 drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] filter">
                The Race <span className="text-white">is On</span>
              </span>
            </h1>
            <h1 className="text-[4vw] lg:text-[3.5vw] font-black leading-none tracking-tighter text-white mb-8 whitespace-nowrap">
              How would you call it?
            </h1>
            <p className="text-lg lg:text-xl font-medium text-gray-400 max-w-lg leading-relaxed mb-12">
              Every weekend, F1 strategists take split-second decisions worth millions, impacting wins, championships & careers. Interval.ai puts you at the pitwall — with the same live data at your fingertips. Now you control the input. Then see what actually happened.
            </p>
            <div>
              <Link
                href="/signup"
                className="group relative inline-flex items-center justify-center px-8 py-4 text-sm font-bold uppercase tracking-widest text-white transition-all rounded-sm overflow-hidden"
                style={{ backgroundColor: '#2596be' }}
              >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                <span className="relative z-10">Make Your First Call →</span>
              </Link>
            </div>
          </div>

          {/* Right Image */}
          <div className="relative h-[50vh] lg:h-auto w-full order-1 lg:order-2">
            <Image
              src="/images/hero.png"
              alt="F1 Car on Track"
              fill
              className="object-cover object-center grayscale contrast-125 lg:object-left"
              priority
            />
            {/* Gradient Overlay for blending */}
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black lg:bg-gradient-to-r lg:from-black lg:via-transparent lg:to-transparent" />
          </div>

        </section>

        {/* HOW IT WORKS GRID */}
        <section className="mx-auto max-w-7xl px-4 py-24 border-b border-white/10">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-black text-white leading-tight mb-8">
              F1 is the most data-rich sport on earth. Now you can step inside it.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-[400px]">

            {/* 01. THE MOMENT (Large) */}
            <div className="group relative col-span-1 md:col-span-2 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 block">
              <Image
                src="/images/moment-background.jpg"
                alt="F1 Race Moment"
                fill
                className="object-cover transition-transform duration-700 group-hover:scale-105 opacity-60 group-hover:opacity-40"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-90" />
              <div className="absolute bottom-0 left-0 p-8 w-full max-w-2xl">
                <span className="mb-2 block text-sm font-bold uppercase tracking-widest text-[#2596be]">
                  01. The Moment
                </span>
                <h3 className="text-3xl font-bold uppercase tracking-tight text-white mb-3">
                  Lap 47. Rain Incoming.
                </h3>
                <p className="text-white/80 font-serif text-lg leading-relaxed">
                  A race situation, frozen in time. Lap 47. Two drivers on different compounds. Rain on the radar. A championship to fight for. What do you do?
                </p>
              </div>
            </div>

            {/* 02. YOUR CALL (Vertical) */}
            <div className="group relative col-span-1 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 block">
              <div className="absolute inset-0 flex flex-col justify-end p-8">
                <span className="mb-2 block text-sm font-bold uppercase tracking-widest text-[#2596be]">
                  02. Your Call
                </span>
                <h3 className="text-2xl font-black uppercase tracking-tighter text-white leading-tight mb-3">
                  You Make The Call
                </h3>
                <p className="text-white/70 font-serif text-base leading-relaxed">
                  You decide — with the real-live data available at your fingertips. Not hindsight. Not a highlight reel. The real picture, at the real moment. Make the call and track the impact to the rest of the race.
                </p>
              </div>
            </div>

            {/* 03. THE OUTCOME (Small) */}
            <div className="group relative col-span-1 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 flex items-center justify-center text-center p-6">
              <Image
                src="https://images.unsplash.com/photo-1533630654593-b2af8d313201?q=80&w=2600&auto=format&fit=crop"
                alt="Race Outcome"
                fill
                className="object-cover transition-transform duration-700 group-hover:scale-110 opacity-40 group-hover:opacity-30"
              />
              <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/90" />
              <div className="relative z-10 p-6 flex flex-col h-full justify-end text-left w-full">
                <span className="block text-sm font-bold uppercase tracking-widest text-[#2596be] mb-2">03. The Outcome</span>
                <h3 className="text-xl font-bold uppercase tracking-wide text-white mb-2">The Reality</h3>
                <p className="text-white/70 font-serif text-sm leading-relaxed">
                  The race plays out. You see where your strategy went, why it happened, and where your thinking was right — or where the data was telling you something you missed.
                </p>
              </div>
            </div>

            {/* 04. HEAD-TO-HEAD (Wide) */}
            <div className="group relative col-span-1 md:col-span-2 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 block">
              <Image
                src="https://images.unsplash.com/photo-1615155172671-db9b53147816?q=80&w=2600&auto=format&fit=crop"
                alt="Head to Head"
                fill
                className="object-cover transition-transform duration-700 group-hover:scale-105 opacity-50"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/40 to-transparent" />
              <div className="absolute inset-0 flex flex-col justify-center p-8 md:p-12 max-w-xl">
                <span className="mb-2 block text-sm font-bold uppercase tracking-widest text-[#2596be]">
                  04. Head-to-Head
                </span>
                <h3 className="text-3xl font-bold uppercase tracking-tight text-white mb-3">
                  The Results
                </h3>
                <p className="text-white/80 font-serif text-lg leading-relaxed">
                  See where your results take you. Real-time, side-by-side analysis versus the live event. Race head-to-head while watching on the screen.
                </p>
              </div>
            </div>

          </div>
        </section>

        {/* WHY WE EXIST SECTION */}
        <section className="bg-black py-32 px-4">
          <div className="mx-auto max-w-4xl">
            <span className="block text-[#2596be] font-bold tracking-widest uppercase text-sm mb-6">Why We Exist</span>

            <h2 className="text-3xl md:text-5xl font-black text-white leading-tight mb-8">
              F1 is the most data-rich sport on earth. Now you can step inside it.
            </h2>

            <div className="space-y-6 text-lg md:text-xl font-medium text-white/80 leading-relaxed max-w-3xl">
              <p>
                Every Grand Prix generates millions of data points — telemetry, tire models, weather, gap analysis. The teams use it to make decisions in seconds. The rest of us watch what happens next and wonder why.
              </p>
              <p>
                Interval.ai closes that gap. We capture every decision, every outcome, every consequence — and let you test your instincts against reality.
              </p>
              <p className="text-white pt-4 font-bold">
                Not a simulation. Real races. Real data. Known outcomes.
              </p>
            </div>
          </div>
        </section>

        {/* STATS COUNTER SECTION */}
        <StatsCounter />

        {/* FEATURE CARDS SECTION */}
        <section className="mx-auto max-w-7xl px-4 pb-24 border-t border-white/10 pt-24">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">

            {/* Paddock Feature */}
            <Link href="/frontend/userpaddock" className="group block space-y-6 p-8 border border-white bg-black hover:bg-white transition-all duration-300 rounded-sm relative overflow-hidden">
              <div className="h-12 w-12 flex items-center justify-center border border-white rounded-full text-white group-hover:border-black group-hover:text-black transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white group-hover:text-black mb-2 transition-colors">The Paddock</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-black/80 transition-colors">
                  <span className="text-white font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2 group-hover:text-black">The Story Behind The Call.</span>
                  Narrative, context, human drama.
                </p>
              </div>
            </Link>

            {/* Pitwall Feature */}
            <Link href="/frontend/userpitwall" className="group block space-y-6 p-8 border border-white bg-black hover:bg-white transition-all duration-300 rounded-sm relative overflow-hidden">
              <div className="h-12 w-12 flex items-center justify-center border border-white rounded-full text-white group-hover:border-black group-hover:text-black transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white group-hover:text-black mb-2 transition-colors">The Pitwall</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-black/80 transition-colors">
                  <span className="text-white font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2 group-hover:text-black">The Data You Needed.</span>
                  Strategy breakdowns, real telemetry moments.
                </p>
              </div>
            </Link>

            {/* Factory Feature */}
            <Link href="/frontend/userfactory" className="group block space-y-6 p-8 border border-white bg-black hover:bg-white transition-all duration-300 rounded-sm relative overflow-hidden">
              <div className="h-12 w-12 flex items-center justify-center border border-white rounded-full text-white group-hover:border-black group-hover:text-black transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.423 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.423 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.703.127 1.5.876 2.683 2.626 2.763 2.898.04.137-.059.279-.197.279h-.7a.75.75 0 01-.75-.75S16.142 5.6 9.875 5.25m6.656 7.625l-1.31-2.098c-.297-.476-.413-1.056-.32-1.623.196-1.19.866-2.27 1.838-2.955" />
                </svg>
              </div>
              <div>
                <h3 className="text-xl font-bold uppercase tracking-widest text-white group-hover:text-black mb-2 transition-colors">The Factory</h3>
                <p className="text-white/60 font-serif text-lg leading-relaxed group-hover:text-black/80 transition-colors">
                  <span className="text-white font-bold not-italic font-sans text-sm uppercase tracking-wider mr-2 group-hover:text-black">The Source.</span>
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
