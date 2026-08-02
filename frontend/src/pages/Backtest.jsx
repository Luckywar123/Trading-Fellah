import { useEffect, useState, useCallback, useRef } from 'react'
import { Loader2, FlaskConical, Play, Radio } from 'lucide-react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import LinkAccountForm from '../components/LinkAccountForm.jsx'

const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AUDUSD', 'USDCAD', 'BTCUSD']
const TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']
const PRESETS = ['conservative', 'balanced', 'aggressive', 'full_send']

export default function Backtest() {
  const { selected, accounts } = useAccounts()
  const [form, setForm] = useState({
    symbol: 'EURUSD', timeframe: '15m', risk_preset: 'balanced', starting_equity: 1000,
    date_from: pastDate(90), date_to: today(),
  })
  const [run, setRun] = useState(null)
  const [runs, setRuns] = useState([])
  const [busy, setBusy] = useState(false)
  const pollRef = useRef(null)

  const [ftForm, setFtForm] = useState({ symbol: 'EURUSD', timeframe: '15m' })
  const [ftTrades, setFtTrades] = useState([])
  const [ftBusy, setFtBusy] = useState(false)

  const loadRuns = useCallback(async () => {
    try { setRuns(await api.listBacktests()) } catch { /* ignore */ }
  }, [])

  const loadFtTrades = useCallback(async () => {
    if (!selected) return
    try { setFtTrades(await api.forwardTestTrades(selected.id)) } catch { /* ignore */ }
  }, [selected])

  useEffect(() => { loadRuns(); loadFtTrades() }, [loadRuns, loadFtTrades])
  useEffect(() => () => clearInterval(pollRef.current), [])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setRun(null)
    try {
      const { run_id } = await api.runBacktest({ ...form, mt5_account_id: selected.id, starting_equity: parseFloat(form.starting_equity) })
      pollRef.current = setInterval(async () => {
        const r = await api.getBacktest(run_id)
        setRun(r)
        if (r.status === 'done' || r.status === 'failed') {
          clearInterval(pollRef.current)
          setBusy(false)
          loadRuns()
        }
      }, 2000)
    } catch (e2) {
      setBusy(false)
      setRun({ status: 'failed', result_summary: { error: e2.message } })
    }
  }

  const toggleForwardTest = async (enabled) => {
    setFtBusy(true)
    try {
      await api.toggleForwardTest(selected.id, { ...ftForm, enabled })
    } finally {
      setFtBusy(false)
    }
  }

  if (accounts.length === 0) return <LinkAccountForm />

  const summary = run?.result_summary
  const curve = run?.equity_curve || []

  return (
    <div className="space-y-6">
      <h1 className="font-display text-xl font-semibold flex items-center gap-2">
        <FlaskConical size={20} className="text-amber" /> Backtest &amp; Forward Test
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <form onSubmit={submit} className="panel p-5 space-y-3 h-fit">
          <div className="text-sm font-semibold mb-1">Jalankan Backtest</div>
          <Select label="Symbol" value={form.symbol} onChange={set('symbol')} options={SYMBOLS} />
          <Select label="Timeframe" value={form.timeframe} onChange={set('timeframe')} options={TIMEFRAMES} />
          <Select label="Risk preset" value={form.risk_preset} onChange={set('risk_preset')} options={PRESETS} />
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-ink-muted font-mono">Dari</label>
              <input type="date" value={form.date_from} onChange={set('date_from')} className="w-full mt-1 bg-raised border border-line rounded-md px-2 py-2 text-xs font-mono focus-ring" />
            </div>
            <div>
              <label className="text-xs text-ink-muted font-mono">Sampai</label>
              <input type="date" value={form.date_to} onChange={set('date_to')} className="w-full mt-1 bg-raised border border-line rounded-md px-2 py-2 text-xs font-mono focus-ring" />
            </div>
          </div>
          <div>
            <label className="text-xs text-ink-muted font-mono">Starting equity ($)</label>
            <input value={form.starting_equity} onChange={set('starting_equity')} className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring" />
          </div>
          <button type="submit" disabled={busy} className="w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {busy ? 'Menjalankan…' : 'Run Backtest'}
          </button>

          <div className="pt-4 mt-2 border-t border-line space-y-3">
            <div className="text-sm font-semibold flex items-center gap-1.5"><Radio size={14} className="text-cyan" /> Forward Test (live, paper)</div>
            <Select label="Symbol" value={ftForm.symbol} onChange={(e) => setFtForm((f) => ({ ...f, symbol: e.target.value }))} options={SYMBOLS} />
            <Select label="Timeframe" value={ftForm.timeframe} onChange={(e) => setFtForm((f) => ({ ...f, timeframe: e.target.value }))} options={TIMEFRAMES} />
            <div className="grid grid-cols-2 gap-2">
              <button type="button" disabled={ftBusy} onClick={() => toggleForwardTest(true)} className="py-2 rounded-md text-xs font-semibold border border-long/40 text-long bg-long/10 hover:bg-long/20 transition">Nyalakan</button>
              <button type="button" disabled={ftBusy} onClick={() => toggleForwardTest(false)} className="py-2 rounded-md text-xs font-semibold border border-line text-ink-muted hover:border-short hover:text-short transition">Matikan</button>
            </div>
            <p className="text-[11px] text-ink-faint leading-relaxed">
              Jalan pakai harga real-time MT5, tapi order cuma dicatat (paper) — gak pernah kirim order asli.
              Sistem cek tiap 5 menit lewat scheduler backend.
            </p>
          </div>
        </form>

        <div className="lg:col-span-2 space-y-4">
          {summary && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <ResultStat label="Win Rate" value={`${summary.win_rate ?? 0}%`} />
              <ResultStat label="Total Trades" value={summary.total_trades ?? 0} />
              <ResultStat label="Net P/L" value={`$${summary.net_pnl ?? 0}`} tone={(summary.net_pnl ?? 0) >= 0 ? 'positive' : 'negative'} />
              <ResultStat label="Max Drawdown" value={`${summary.max_drawdown_pct ?? 0}%`} tone="negative" />
            </div>
          )}
          {summary?.error && <div className="panel border-short/40 bg-short/10 p-3 text-sm text-short">{summary.error}</div>}

          <div className="panel p-5">
            <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Equity Curve (Backtest)</div>
            {curve.length > 1 ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={curve}>
                  <defs>
                    <linearGradient id="btEq" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4FD1C5" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#4FD1C5" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#2A3035" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="t" stroke="#5A6166" tick={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }} minTickGap={40} />
                  <YAxis stroke="#5A6166" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: '#1E2327', border: '1px solid #2A3035', borderRadius: 8, fontFamily: 'IBM Plex Mono', fontSize: 12 }} />
                  <Area type="monotone" dataKey="equity" stroke="#4FD1C5" fill="url(#btEq)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[260px] flex items-center justify-center text-sm text-ink-faint font-mono">
                {busy ? 'Menjalankan backtest…' : 'Belum ada hasil — jalankan backtest di sebelah kiri'}
              </div>
            )}
          </div>

          <div className="panel p-5">
            <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Forward Test Trades (paper, terbaru)</div>
            {ftTrades.length === 0 ? (
              <p className="text-sm text-ink-faint py-4">Belum ada trade forward test.</p>
            ) : (
              <table className="w-full text-sm font-mono">
                <tbody>
                  {ftTrades.slice(0, 10).map((t) => (
                    <tr key={t.id} className="border-b border-line/50">
                      <td className="py-2">{t.symbol}</td>
                      <td className={t.direction === 'LONG' ? 'text-long' : 'text-short'}>{t.direction}</td>
                      <td className="text-ink-muted">{t.source}</td>
                      <td className="text-ink-muted">{new Date(t.opened_at).toLocaleString('id-ID')}</td>
                      <td className={`text-right ${t.pnl_usd >= 0 ? 'text-long' : 'text-short'}`}>
                        {t.pnl_usd != null ? `${t.pnl_usd >= 0 ? '+' : ''}$${t.pnl_usd}` : 'open'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Select({ label, value, onChange, options }) {
  return (
    <div>
      <label className="text-xs text-ink-muted font-mono">{label}</label>
      <select value={value} onChange={onChange} className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring">
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

function ResultStat({ label, value, tone = 'neutral' }) {
  const color = { neutral: 'text-ink', positive: 'text-long', negative: 'text-short' }[tone]
  return (
    <div className="panel p-3.5">
      <div className="text-[10px] uppercase tracking-widest text-ink-faint font-mono">{label}</div>
      <div className={`text-lg font-mono font-semibold mt-1 ${color}`}>{value}</div>
    </div>
  )
}

function today() { return new Date().toISOString().slice(0, 10) }
function pastDate(days) { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10) }
