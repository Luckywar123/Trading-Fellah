import { useEffect, useState, useCallback } from 'react'
import { Loader2, Newspaper, Brain, BookOpen, RefreshCw } from 'lucide-react'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import LinkAccountForm from '../components/LinkAccountForm.jsx'

const SENTIMENT_STYLE = {
  buy: 'text-long bg-long/10 border-long/30',
  sell: 'text-short bg-short/10 border-short/30',
  neutral: 'text-ink-muted bg-raised border-line',
}

export default function AIInsights() {
  const { selected, accounts } = useAccounts()
  const [news, setNews] = useState([])
  const [newsBusy, setNewsBusy] = useState(false)
  const [behavior, setBehavior] = useState(null)
  const [behaviorBusy, setBehaviorBusy] = useState(false)
  const [knowledge, setKnowledge] = useState([])
  const [kbForm, setKbForm] = useState({ title: '', content: '', tags: '' })
  const [kbBusy, setKbBusy] = useState(false)
  const [err, setErr] = useState(null)

  const loadNews = useCallback(async () => {
    try { setNews(await api.news()) } catch { /* ignore */ }
  }, [])
  const loadKnowledge = useCallback(async () => {
    try { setKnowledge(await api.listKnowledge()) } catch { /* ignore */ }
  }, [])
  const loadBehavior = useCallback(async () => {
    try { setBehavior(await api.latestBehavior()) } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadNews(); loadKnowledge(); loadBehavior() }, [loadNews, loadKnowledge, loadBehavior])

  const refreshNews = async () => {
    setNewsBusy(true)
    setErr(null)
    try {
      await api.refreshNews()
      await loadNews()
    } catch (e) {
      setErr(e.message)
    } finally {
      setNewsBusy(false)
    }
  }

  const generateBehavior = async () => {
    if (!selected) return
    setBehaviorBusy(true)
    setErr(null)
    try {
      setBehavior(await api.generateBehavior(selected.id))
    } catch (e) {
      setErr(e.message)
    } finally {
      setBehaviorBusy(false)
    }
  }

  const submitKnowledge = async (e) => {
    e.preventDefault()
    setKbBusy(true)
    try {
      await api.addKnowledge({ ...kbForm, tags: kbForm.tags.split(',').map((t) => t.trim()).filter(Boolean) })
      setKbForm({ title: '', content: '', tags: '' })
      loadKnowledge()
    } catch (e) {
      setErr(e.message)
    } finally {
      setKbBusy(false)
    }
  }

  if (accounts.length === 0) return <LinkAccountForm />

  return (
    <div className="space-y-6">
      <h1 className="font-display text-xl font-semibold flex items-center gap-2">
        <Brain size={20} className="text-amber" /> AI Insights
      </h1>
      {err && <div className="panel border-short/40 bg-short/10 p-3 text-sm text-short">{err}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* --- News sentiment --- */}
        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold flex items-center gap-1.5"><Newspaper size={15} className="text-amber" /> News Sentiment</div>
            <button onClick={refreshNews} disabled={newsBusy} className="flex items-center gap-1.5 text-xs font-mono text-ink-muted hover:text-amber transition px-2.5 py-1 rounded-md border border-line">
              <RefreshCw size={12} className={newsBusy ? 'animate-spin' : ''} /> Refresh
            </button>
          </div>
          {news.length === 0 ? (
            <p className="text-sm text-ink-faint py-6 text-center">
              Belum ada data berita. Set <span className="font-mono">NEWS_API_KEY</span> di backend .env, terus klik Refresh.
            </p>
          ) : (
            <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-1">
              {news.map((n) => (
                <div key={n.id} className="bg-raised border border-line rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-ink leading-snug">{n.headline}</p>
                    <span className={`shrink-0 text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${SENTIMENT_STYLE[n.sentiment] || SENTIMENT_STYLE.neutral}`}>
                      {n.sentiment}
                    </span>
                  </div>
                  {n.ai_summary && <p className="text-xs text-ink-muted mt-1.5">{n.ai_summary}</p>}
                  <div className="flex items-center gap-2 mt-2 text-[10px] font-mono text-ink-faint">
                    <span className="uppercase">{n.impact_level} impact</span>
                    {n.currency_impact?.length > 0 && <span>· {n.currency_impact.join(', ')}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* --- Behavior profile --- */}
        <div className="panel p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm font-semibold flex items-center gap-1.5"><Brain size={15} className="text-cyan" /> Trading Behavior Profile</div>
            <button onClick={generateBehavior} disabled={behaviorBusy} className="flex items-center gap-1.5 text-xs font-mono text-ink-muted hover:text-cyan transition px-2.5 py-1 rounded-md border border-line">
              {behaviorBusy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Generate
            </button>
          </div>
          {!behavior ? (
            <p className="text-sm text-ink-faint py-6 text-center">
              Belum ada profil. Butuh minimal 5 trade histori (closed) buat akun aktif, terus klik Generate.
            </p>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-ink leading-relaxed">{behavior.summary}</p>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <Metric label="Overtrading score" value={behavior.tendencies?.overtrading_score} />
                <Metric label="Discipline score" value={behavior.tendencies?.discipline_score} />
                <Metric label="Sesi terbaik" value={behavior.tendencies?.best_session} isText />
                <Metric label="Symbol terbaik" value={behavior.tendencies?.best_symbol} isText />
              </div>
              {behavior.tendencies?.revenge_trading_flag && (
                <p className="text-xs text-short bg-short/10 border border-short/30 rounded-md px-3 py-2">
                  ⚠ Terdeteksi pola revenge trading (entry besar/cepat setelah loss beruntun).
                </p>
              )}
              {behavior.recommendations && (
                <div className="bg-raised border border-line rounded-lg p-3 text-xs text-ink-muted leading-relaxed">
                  <strong className="text-ink">Saran AI:</strong> {behavior.recommendations}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* --- Knowledge base --- */}
      <div className="panel p-5">
        <div className="text-sm font-semibold flex items-center gap-1.5 mb-1"><BookOpen size={15} className="text-amber" /> Materi Financial (Knowledge Base AI)</div>
        <p className="text-xs text-ink-muted mb-4">
          Materi yang kamu tambahin di sini dipakai AI sebagai konteks tambahan pas bikin analisa/rationale entry.
        </p>
        <form onSubmit={submitKnowledge} className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          <input placeholder="Judul" value={kbForm.title} onChange={(e) => setKbForm((f) => ({ ...f, title: e.target.value }))} required
            className="bg-raised border border-line rounded-md px-3 py-2 text-sm focus-ring" />
          <input placeholder="Tags (pisah koma, contoh: EURUSD, order_block)" value={kbForm.tags} onChange={(e) => setKbForm((f) => ({ ...f, tags: e.target.value }))}
            className="bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring" />
          <textarea placeholder="Isi materi…" value={kbForm.content} onChange={(e) => setKbForm((f) => ({ ...f, content: e.target.value }))} required rows={3}
            className="sm:col-span-2 bg-raised border border-line rounded-md px-3 py-2 text-sm focus-ring resize-none" />
          <button type="submit" disabled={kbBusy} className="sm:col-span-2 bg-amber text-void font-semibold text-sm rounded-md py-2.5 hover:brightness-110 transition disabled:opacity-60">
            {kbBusy ? 'Menyimpan…' : 'Tambah Materi'}
          </button>
        </form>
        <div className="flex flex-wrap gap-2">
          {knowledge.map((k) => (
            <span key={k.id} className="text-xs font-mono bg-raised border border-line rounded-full px-3 py-1 text-ink-muted">{k.title}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function Metric({ label, value, isText }) {
  return (
    <div className="bg-raised border border-line rounded-md p-2.5">
      <div className="text-[10px] text-ink-faint uppercase tracking-wider">{label}</div>
      <div className="text-sm text-ink mt-0.5">{isText ? (value || '-') : value != null ? `${(value * 100).toFixed(0)}%` : '-'}</div>
    </div>
  )
}
