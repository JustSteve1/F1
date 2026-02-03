"use client"

import { useState } from "react"

export default function PitwallPage() {
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([
        { role: 'assistant', content: 'Welcome to the Pitwall. Ask me anything about F1 data.' }
    ])
    const [input, setInput] = useState("")

    const handleSubmit = (e: React.FormEvent) => {
        const handleSubmit = async (e: React.FormEvent) => {
            e.preventDefault()
            if (!input.trim()) return

            setMessages(prev => [...prev, { role: 'user', content: input }])
            setInput("")

            // Call API
            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: input })
                })
                const data = await res.json()

                if (data.error) {
                    setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }])
                } else {
                    setMessages(prev => [...prev, { role: 'assistant', content: data.content }])
                    // In a real app, we would pass data.data to the chart component here
                    console.log("Chart Data:", data.data)
                }
            } catch (err) {
                setMessages(prev => [...prev, { role: 'assistant', content: "Failed to connect to server." }])
            }
        }

        return (
            <div className="flex h-screen overflow-hidden">
                {/* Sidebar / Chat */}
                <div className="w-1/3 border-r border-white/20 flex flex-col bg-black">
                    <header className="p-4 border-b border-white/20">
                        <h1 className="font-bold text-lg">Pitwall Chat</h1>
                    </header>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.map((m, i) => (
                            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] p-3 text-sm ${m.role === 'user' ? 'bg-white text-black' : 'border border-white/20'}`}>
                                    {m.content}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="p-4 border-t border-white/20">
                        <form onSubmit={handleSubmit}>
                            <input
                                className="w-full bg-black border border-white/50 p-2 text-white outline-none focus:border-white"
                                placeholder="Ask about lap times, tyre strategies..."
                                value={input}
                                onChange={e => setInput(e.target.value)}
                            />
                        </form>
                    </div>
                </div>

                {/* Canvas / Visualization */}
                <div className="flex-1 bg-black p-8 flex items-center justify-center">
                    <div className="text-gray-500 text-center">
                        <p className="mb-4">Visualization Canvas</p>
                        <div className="border border-dashed border-gray-700 w-96 h-64 flex items-center justify-center">
                            Chart Placeholder
                        </div>
                    </div>
                </div>
            </div>
        )
    }
