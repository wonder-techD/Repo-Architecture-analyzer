import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, MessageCircle } from 'lucide-react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function ChatPanel({ jobId, className = '' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e) {
    e.preventDefault()
    const q = input.trim()
    if (!q || !jobId || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const { data } = await axios.post(`${API_BASE}/ask/${jobId}`, { question: q })
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }])
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to get answer.'
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`flex flex-col rounded-xl border border-white/10 bg-codeRepo-surface min-h-[420px] h-[calc(100vh-6rem)] max-h-[calc(100vh-6rem)] ${className}`}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 shrink-0">
        <MessageCircle className="w-4 h-4 text-indigo-400" />
        <span className="text-sm font-medium text-white">AI Chat</span>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 min-h-0"
      >
        {messages.length === 0 && (
          <p className="text-sm text-slate-500 text-center py-8">
            Ask anything about this codebase. Answers use the generated documentation.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg px-3 py-2 text-sm ${
              m.role === 'user'
                ? 'bg-indigo-500/20 text-white ml-4'
                : 'bg-white/5 text-slate-300 mr-4'
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-slate-500 text-sm py-2">
            <Loader2 className="w-4 h-4 animate-spin shrink-0" />
            <span>Thinking…</span>
          </div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
        <div className="flex rounded-lg border border-white/10 bg-codeRepo-bg overflow-hidden">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this repo…"
            className="flex-1 px-4 py-3 bg-transparent text-white placeholder-slate-500 focus:outline-none text-sm"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-3 text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-50 transition"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
