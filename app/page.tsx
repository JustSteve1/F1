import Image from "next/image";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

export default function Home() {
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

            {/* Item 1: Large Feature */}
            <div className="group relative col-span-1 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500">
              <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80" />
              <div className="absolute bottom-0 left-0 p-8">
                <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-indigo-400">Latest News</span>
                <h3 className="text-3xl font-bold uppercase tracking-tight text-white group-hover:text-indigo-400 transition-colors">
                  New Regulations for 2026
                </h3>
                <p className="mt-2 line-clamp-2 text-white/60">
                  The FIA announces groundbreaking changes to the technical regulations, focusing on sustainability and closer racing.
                </p>
              </div>
            </div>

            {/* Item 2: Vertical Highlight */}
            <div className="group relative col-span-1 row-span-1 md:row-span-2 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500">
              <div className="absolute inset-0 flex flex-col justify-between p-8">
                <div>
                  <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-emerald-400">Standings</span>
                  <h3 className="text-4xl font-black uppercase tracking-tighter text-white">
                    Leclerc <br /> Domination
                  </h3>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between border-b border-white/10 pb-2">
                    <span className="font-mono text-white/50">01</span>
                    <span className="font-bold">LEC</span>
                    <span className="text-emerald-400">245 PTS</span>
                  </div>
                  <div className="flex justify-between border-b border-white/10 pb-2">
                    <span className="font-mono text-white/50">02</span>
                    <span className="font-bold">VER</span>
                    <span className="text-white/70">210 PTS</span>
                  </div>
                  <div className="flex justify-between border-b border-white/10 pb-2">
                    <span className="font-mono text-white/50">03</span>
                    <span className="font-bold">NOR</span>
                    <span className="text-white/70">188 PTS</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Item 3: Media */}
            <div className="group relative col-span-1 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 flex items-center justify-center">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-white/5 group-hover:scale-110 transition-transform">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8 text-white">
                    <path fillRule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clipRule="evenodd" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold uppercase tracking-wide text-white">Watch Highlights</h3>
                <p className="mt-1 text-sm text-white/50">Grand Prix of Monaco</p>
              </div>
            </div>

            {/* Item 4: Quote */}
            <div className="group relative col-span-1 lg:col-span-2 row-span-1 overflow-hidden rounded-sm border border-white/10 bg-white/5 hover:border-white/30 transition-all duration-500 p-12 flex items-center">
              <blockquote className="text-2xl md:text-3xl font-light italic leading-relaxed text-white/80">
                &quot;When you are fitted in a racing car and you race to win, second or third place is not enough.&quot;
                <footer className="mt-4 block text-sm font-bold uppercase not-italic text-white/50">— Ayrton Senna</footer>
              </blockquote>
            </div>

          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
