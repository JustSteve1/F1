import Link from 'next/link'

const DATASETS = [
    {
        id: 'f1-data-2023',
        title: 'Formula 1 World Championship 2023',
        description: 'Complete race data, lap times, and telemetry for the 2023 season.',
        updated: '2023-12-01',
        url: 'https://kaggle.com'
    },
    {
        id: 'f1-historical',
        title: 'F1 Historical Data (1950-2022)',
        description: 'Comprehensive archive of all F1 races, drivers, and constructors.',
        updated: '2023-01-15',
        url: 'https://kaggle.com'
    }
]

export default function DatasetsPage() {
    return (
        <div className="min-h-screen p-8 max-w-5xl mx-auto">
            <header className="mb-12 border-b border-white pb-4">
                <h1 className="text-4xl font-bold mb-2">F1 Datasets</h1>
                <p className="text-gray-400">Curated, high-quality datasets for analysis.</p>
            </header>

            <div className="grid gap-6">
                {DATASETS.map((dataset) => (
                    <div key={dataset.id} className="border border-white/20 p-6 hover:border-white transition-colors">
                        <div className="flex justify-between items-start mb-4">
                            <h2 className="text-2xl font-bold">{dataset.title}</h2>
                            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-1">
                                Updated: {dataset.updated}
                            </span>
                        </div>
                        <p className="mb-6 text-gray-300">{dataset.description}</p>
                        <Link
                            href={dataset.url}
                            target="_blank"
                            className="inline-block bg-white text-black px-4 py-2 font-bold hover:bg-gray-200"
                        >
                            Open on Kaggle &rarr;
                        </Link>
                    </div>
                ))}
            </div>
        </div>
    )
}
