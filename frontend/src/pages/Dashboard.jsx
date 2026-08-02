import { useEffect, useState, useCallback } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import StatCard from '../components/StatCard.jsx'
import RiskGauge from '../components/RiskGauge.jsx'
import LinkAccountForm from '../components/LinkAccountForm.jsx'

export default function Dashboard() {
  const { selected, accounts, loading: acctLoading } = useAccounts()
  const [balance, setBalance] = useState(null)
  const [positions, setPositions] = useState([])
  const [history, setHistory] = useState([])
  const [riskCfg, setRiskCfg] = useState(null)
  const [blackout, setBlackout] = useState(null)
  const [err, setErr] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    if (!selected) return
    setErr(null)
    try {
      const [bal, pos, hist, risk, bo] = await Promise.all([
        api.getBalance(selected.id),
        api.getPositions(selected.id),
        api.history(selected.id).catch(() => []),
        api.getRiskSettings(selected.id).catch(() => null),
        api.blackoutStatus().catch(() => null),
      ])
      setBalance(bal)
      setPositions(pos)
      setHistory(hist)
      setRiskCfg(risk)
      setBlackout(bo)
    } catch (e) {
      setErr(e.message)
    }
  }, [selected])

  useEffect(() => {
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [load])

  const handleRefresh = async () => {
    setRefreshing(true)
    await load()
    setRefreshing(false)
  }

  if (!acctLoading && accounts.length === 0) {
    return (
      <div>
        <h1 className="font-display text-xl font-semibold mb-1">Selamat datang</h1>
        <p className="text-sm text-ink-muted mb-6">Tautkan akun MT5 pertama kamu buat mulai.</p>
        <LinkAccountForm />
      </div>
    )
  }

  const equity = balance?.equity ?? 0
  const marginUsed = balance?.margin ?? 0
  const freeMargin = balance?.free_margin ?? 0
  const marginPct = freeMargin + marginUsed > 0 ? (marginUsed / (freeMargin + marginUsed)) * 100 : 0
  const openPnl = positions.reduce((s, p) => s + (p.profit || 0), 0)

  const closedHistory = history.filter((h) => h.closed_at)
  let running = balance?.balance ?? 1000
  const curve = [...closedHistory].reverse().map((h) => {
    running += h.pnl_usd || 0
    return { t: new Date(h.opened_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short' }), equity: running }
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold">Dashboard</h1>
          <p className="text-sm text-ink-muted">{selected?.label} · {selected?.broker_server}</p>
        </div>
        <button onClick={handleRefresh} className="flex items-center gap-2 text-xs font-mono text-ink-muted hover:text-amber transition focus-ring px-3 py-1.5 rounded-md border border-line">
          <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {blackout?.blackout_active && (
        <div className="panel border-short/40 bg-short/10 p-3 flex items-center gap-2.5 text-sm">
          <AlertTriangle size={16} className="text-short shrink-0" />
          <span className="text-short">News blackout aktif — order otomatis dijeda: <strong>{blackout.headline}</strong></span>
        </div>
      )}
      {err && <div className="panel border-short/40 bg-short/10 p-3 text-sm text-short">{err}</div>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Balance" value={`$${(balance?.balance ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`} />
        <StatCard label="Equity" value={`$${equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} />
        <StatCard label="Floating P/L" value={`${openPnl >= 0 ? '+' : ''}$${openPnl.toFixed(2)}`} tone={openPnl >= 0 ? 'positive' : 'negative'} />
        <StatCard label="Free Margin" value={`$${freeMargin.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub={`Leverage 1:${balance?.leverage ?? '-'}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="panel p-5 lg:col-span-2">
          <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Equity Curve</div>
          {curve.length > 1 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={curve}>
                <defs>
                  <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F0A030" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#F0A030" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#2A3035" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="t" stroke="#5A6166" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                <YAxis stroke="#5A6166" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#1E2327', border: '1px solid #2A3035', borderRadius: 8, fontFamily: 'IBM Plex Mono', fontSize: 12 }} />
                <Area type="monotone" dataKey="equity" stroke="#F0A030" fill="url(#eq)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm text-ink-faint font-mono">
              Belum cukup histori trade buat equity curve
            </div>
          )}
        </div>

        <div className="panel p-5 flex flex-col items-center justify-center">
          <RiskGauge valuePct={marginPct} ceilingPct={riskCfg?.max_margin_pct_per_trade ?? 100} />
          <p className="text-xs text-ink-faint mt-2 text-center leading-relaxed">
            Garis merah = ceiling margin per-order dari Risk Settings kamu
          </p>
        </div>
      </div>

      <div className="panel p-5">
        <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">
          Posisi Terbuka ({positions.length})
        </div>
        {positions.length === 0 ? (
          <p className="text-sm text-ink-faint py-4">Gak ada posisi terbuka saat ini.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-faint text-xs uppercase tracking-wider font-mono border-b border-line">
                <th className="py-2 font-normal">Symbol</th>
                <th className="font-normal">Arah</th>
                <th className="font-normal">Lot</th>
                <th className="font-normal">Entry</th>
                <th className="font-normal">Harga Sekarang</th>
                <th className="font-normal text-right">P/L</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {positions.map((p) => (
                <tr key={p.ticket} className="border-b border-line/50">
                  <td className="py-2.5">{p.symbol}</td>
                  <td className={p.direction === 'LONG' ? 'text-long' : 'text-short'}>{p.direction}</td>
                  <td>{p.volume}</td>
                  <td>{p.open_price}</td>
                  <td>{p.current_price}</td>
                  <td className={`text-right ${p.profit >= 0 ? 'text-long' : 'text-short'}`}>
                    {p.profit >= 0 ? '+' : ''}{p.profit?.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
