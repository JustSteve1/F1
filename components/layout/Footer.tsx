export default function Footer() {
    return (
        <footer className="bg-black py-12 px-6 border-t border-white/10">
            <div className="mx-auto max-w-7xl">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                    <div className="max-w-lg">
                        <h2 className="text-2xl font-black tracking-tighter text-white mb-4 uppercase">Interval.ai</h2>
                        <p className="text-white/60 text-sm leading-relaxed">
                            Interval.ai is building the world&apos;s first continuously grounded dataset of real-world sporting decisions and known outcomes — one race at a time.
                        </p>
                    </div>
                    <div className="flex gap-8">
                        <a href="#" className="text-white/70 hover:text-white transition-colors text-sm">Privacy</a>
                        <a href="#" className="text-white/70 hover:text-white transition-colors text-sm">Terms</a>
                        <a href="#" className="text-white/70 hover:text-white transition-colors text-sm">Contact</a>
                    </div>
                </div>
                <div className="mt-12 pt-8 border-t border-white/5 text-center md:text-left">
                    <p className="text-white/30 text-xs">
                        &copy; {new Date().getFullYear()} Interval.ai Inc. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    );
}
