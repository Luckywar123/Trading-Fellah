import { useEffect, useRef, useState } from 'react'
import { Bot, Loader2, Send, X } from 'lucide-react'
import { api } from '../lib/api.js'

export default function AIChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    const history = messages.slice(-6)
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)
    try {
      const data = await api.chat(text, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Maaf, gagal menjawab: ${e.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Buka asisten AI"
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full bg-amber text-void font-medium shadow-lg hover:opacity-90 transition-opacity focus-ring"
      >
        {open ? <X size={18} /> : <Bot size={18} />}
        <span className="text-sm">{open ? 'Tutup' : 'Asisten AI'}</span>
      </button>

      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-96 max-w-[calc(100vw-3rem)] h-[480px] bg-raised border border-line rounded-xl shadow-2xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-line">
            <div className="font-display font-semibold text-sm">Asisten Trading AI</div>
            <div className="text-xs text-ink-muted">Tanya soal risiko, istilah, atau analisa. Bukan nasihat keuangan.</div>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {messages.length === 0 && (
              <div className="text-xs text-ink-muted text-center py-8">
                Contoh: "Jelaskan order block", "Apa risiko trade saat NFP?"
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`text-sm px-3 py-2 rounded-lg whitespace-pre-wrap ${
                  m.role === 'user' ? 'bg-amber-soft text-ink ml-8' : 'bg-void text-ink mr-8 border border-line'
                }`}
              >
                {m.content}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-xs text-ink-muted">
                <Loader2 size={14} className="animate-spin" /> Berpikir…
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="p-3 border-t border-line flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              maxLength={2000}
              placeholder="Tulis pertanyaan…"
              className="flex-1 bg-void border border-line rounded-md px-3 py-2 text-sm focus-ring"
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              aria-label="Kirim"
              className="px-3 rounded-md bg-amber text-void disabled:opacity-40 focus-ring"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
