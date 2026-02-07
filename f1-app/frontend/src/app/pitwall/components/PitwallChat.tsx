
"use client"

import { useState, useRef, useEffect } from "react"
import { VoiceInput } from "./VoiceInput"

interface Message {
    role: 'user' | 'assistant'
    content: string
}

interface PitwallChatProps {
    messages: Message[]
    loading: boolean
    onSendMessage: (message: string) => void
}

export function PitwallChat({ messages, loading, onSendMessage }: PitwallChatProps) {
    const [input, setInput] = useState("")
    const scrollRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages, loading])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || loading) return
        onSendMessage(input)
        setInput("")
    }

    const handleTranscription = (text: string) => {
        setInput(prev => prev + (prev ? " " : "") + text);
    }

    return (
        <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="p-4 border-b border-white/10 bg-black/40 backdrop-blur-md flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></div>
                    <h2 className="font-bold text-sm tracking-widest text-white/90 uppercase">Pitwall Assistant</h2>
                </div>
                <div className="text-xs text-white/40 font-mono">v1.2</div>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
                {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                        <div
                            className={`max-w-[85%] p-3 text-sm rounded-lg shadow-lg ${m.role === 'user'
                                ? 'bg-white text-black font-medium'
                                : 'bg-zinc-800/80 text-gray-200 border border-white/5 backdrop-blur-sm'
                                }`}
                        >
                            {m.content}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start animate-fade-in">
                        <div className="bg-zinc-800/50 p-3 rounded-lg border border-white/5 flex gap-1 items-center">
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-bounce"></span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 bg-black/40 border-t border-white/10">
                <form onSubmit={handleSubmit} className="relative flex gap-2 items-center">
                    <div className="relative flex-1">
                        <input
                            className="w-full bg-zinc-900/50 border border-white/20 rounded-lg p-3 pr-10 text-white placeholder-gray-500 focus:outline-none focus:border-red-600 transition-colors font-sans text-sm"
                            placeholder="Ask the Pitwall..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || loading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                                <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                            </svg>
                        </button>
                    </div>

                    <VoiceInput onTranscription={handleTranscription} />
                </form>
                <div className="mt-2 text-[10px] text-center text-gray-600 font-mono">
                    AI can make mistakes. Verify critical race data.
                </div>
            </div>
        </div>
    )
}
