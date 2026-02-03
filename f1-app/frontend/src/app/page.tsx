import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 text-center">
      <h1 className="text-6xl font-bold mb-8 tracking-tighter border-b-2 border-white pb-4">
        F1 App
      </h1>
      <p className="text-2xl mb-12 max-w-2xl text-gray-400">
        AI-powered analytics, live race data, and datasets.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-4xl">
        <Link href="/pitwall" className="group border border-white/20 p-8 hover:bg-white hover:text-black transition-all">
          <h2 className="text-2xl font-bold mb-4">Pitwall &rarr;</h2>
          <p className="text-sm opacity-70 group-hover:opacity-100">Chat with your data using Gemini AI.</p>
        </Link>

        <Link href="/live" className="group border border-white/20 p-8 hover:bg-white hover:text-black transition-all">
          <h2 className="text-2xl font-bold mb-4">Live F1 &rarr;</h2>
          <p className="text-sm opacity-70 group-hover:opacity-100">Real-time race telemetry and tracking.</p>
        </Link>

        <Link href="/datasets" className="group border border-white/20 p-8 hover:bg-white hover:text-black transition-all">
          <h2 className="text-2xl font-bold mb-4">Datasets &rarr;</h2>
          <p className="text-sm opacity-70 group-hover:opacity-100">Curated Kaggle datasets for analysis.</p>
        </Link>

        <Link href="/auth/signin" className="group border border-white/20 p-8 hover:bg-white hover:text-black transition-all">
          <h2 className="text-2xl font-bold mb-4">Sign In &rarr;</h2>
          <p className="text-sm opacity-70 group-hover:opacity-100">Access your personalized dashboard.</p>
        </Link>
      </div>
    </main>
  )
}
