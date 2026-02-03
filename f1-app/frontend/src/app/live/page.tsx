export default function LivePage() {
    return (
        <div className="flex h-screen flex-col">
            <header className="border-b border-white/20 p-4">
                <h1 className="text-xl font-bold">Live F1 Data</h1>
            </header>
            <main className="flex-1 overflow-hidden relative bg-neutral-900">
                <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                    <p>Live Race Data Placeholder (Integrate f1-race-replay here)</p>
                    {/* <iframe 
                src="PLACEHOLDER_URL" 
                className="w-full h-full border-none"
                title="Live F1"
            /> */}
                </div>
            </main>
        </div>
    )
}
