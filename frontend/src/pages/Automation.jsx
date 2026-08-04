import { useEffect, useState, useCallback } from 'react'
import { Bot, Radio, Zap, Plus, Trash2, Loader2 } from 'lucide-react'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import LinkAccountForm from '../components/LinkAccountForm.jsx'
import ConfirmModal from '../components/ConfirmModal.jsx'

const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AUDUSD', 'USDCAD', 'BTCUSD']
const TIMEFRAMES = ['5m', '15m', '1h', '4h']

export default function Automation() {
  const { selected, accounts } = useAccounts()
  const [riskCfg, setRiskCfg] = useState(null)
  const [liveSymbols, setLiveSymbols] = useState([])
  const [ftTrades, setFtTrades] = useState([])
  const [newSymbolForm, setNewSymbolForm] = useState({ symbol: 'EURUSD', timeframe: '15m' })
  const [ftForm, setFtForm] = useState({ symbol: 'EURUSD', timeframe: '15m' })
  const [showConfirm, setShowConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const load = useCallback(async () => {
    if (!selected) return
    try {
      const [risk, syms, trades] = await Promise.all([
        api.getRiskSettings(selected.id),
        api.listAutotradeSymbols(selected.id),
        api.forwardTestTrades(selected.id).catch(() => []),
      ])
      setRiskCfg(risk)
      setLiveSymbols(syms)
      setFtTrades(trades)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }, [selected])

  useEffect(() => { load() }, [load])

  const enableMaster = async () => {
    setBusy(true)
    try {
      const updated = await api.updateRiskSettings(selected.id, { live_autotrade_enabled: true })
      setRiskCfg(updated)
      setShowConfirm(false)
      setMsg({ type: 'ok', text: 'Live auto-trade AKTIF. AI sekarang bisa masang order asli buat simbol yang kamu watchlist di bawah.' })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const disableMaster = async () => {
    setBusy(true)
    try {
      const updated = await api.updateRiskSettings(selected.id, { live_autotrade_enabled: false })
      setRiskCfg(updated)
      setMsg({ type: 'ok', text: 'Live auto-trade dimatikan.' })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const emergencyStop = async () => {
    if (!window.confirm('Ini bakal matiin auto-trade DAN nutup SEMUA posisi terbuka di akun ini sekarang juga. Lanjut?')) return
    setBusy(true)
    try {
      const res = await api.emergencyStop(selected.id)
      setMsg({ type: 'ok', text: `Emergency stop dijalankan. ${res.positions_closed.length} posisi ditutup.` })
      load()
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const addLiveSymbol = async () => {
    setBusy(true)
    try {
      await api.toggleAutotradeSymbol(selected.id, { ...newSymbolForm, enabled: true })
      load()
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const removeLiveSymbol = async (symbol, timeframe) => {
    setBusy(true)
    try {
      await api.toggleAutotradeSymbol(selected.id, { symbol, timeframe, enabled: false })
      load()
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const toggleForwardTest = async (enabled) => {
    setBusy(true)
    try {
      await api.toggleForwardTest(selected.id, { ...ftForm, enabled })
      setMsg({ type: 'ok', text: enabled ? 'Forward test dinyalain.' : 'Forward test dimatiin.' })
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  if (accounts.length === 0) return <LinkAccountForm />
  if (!riskCfg) return <div className="text-sm text-ink-muted font-mono">Memuat…</div>

  const isLive = riskCfg.live_autotrade_enabled
  const activeSymbols = liveSymbols.filter((s) => s.enabled)

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="font-display text-xl font-semibold flex items-center gap-2">
        <Bot size={20} className="text-amber" /> Automation
      </h1>
      {msg && <p className={`text-xs ${msg.type === 'ok' ? 'text-long' : 'text-short'}`}>{msg.text}</p>}

      {/* --- LIVE AUTO-TRADE (danger zone) --- */}
      <div className={`panel p-5 space-y-4 ${isLive ? 'border-short/50' : ''}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap size={16} className={isLive ? 'text-short' : 'text-ink-muted'} />
            <div>
              <div className="text-sm font-semibold">Live Auto-Trade</div>
              <div className="text-xs text-ink-faint">AI eksekusi order ASLI otomatis — {selected?.label} ({selected?.mt5_login})</div>
            </div>
          </div>
          <span className={`text-xs font-mono px-2.5 py-1 rounded-full border ${isLive ? 'border-short/50 text-short bg-short/10 animate-pulse' : 'border-line text-ink-faint'}`}>
            {isLive ? '● LIVE' : '○ OFF'}
          </span>
        </div>

        <p className="text-xs text-ink-muted leading-relaxed">
          Kalau nyala: tiap 5 menit sistem cek simbol di watchlist bawah, dan kalau AI
          nemuin breakout swing/order block/support-resistance yang tervalidasi (lolos
          ambang confidence di Risk Settings), order ASLI langsung dipasang pakai lot
          sesuai preset risk kamu (termasuk Full Margin Mode kalau nyala). News blackout
          net dan circuit breaker tetap berlaku sebagai pengaman.
        </p>

        <div className="flex gap-2">
          {!isLive ? (
            <button onClick={() => setShowConfirm(true)} disabled={busy || activeSymbols.length === 0}
              className="flex-1 py-2.5 rounded-md text-sm font-semibold bg-short text-void hover:brightness-110 transition disabled:opacity-40">
              Nyalakan Live Auto-Trade
            </button>
          ) : (
            <button onClick={disableMaster} disabled={busy}
              className="flex-1 py-2.5 rounded-md text-sm font-semibold border border-line text-ink hover:bg-raised transition">
              Matikan
            </button>
          )}
          <button onClick={emergencyStop} disabled={busy}
            className="px-4 py-2.5 rounded-md text-sm font-semibold bg-raised border border-short/40 text-short hover:bg-short/10 transition">
            🛑 Emergency Stop
          </button>
        </div>
        {!isLive && activeSymbols.length === 0 && (
          <p className="text-[11px] text-amber">Tambah minimal 1 simbol ke watchlist dulu di bawah sebelum bisa dinyalain.</p>
        )}

        <div className="pt-3 border-t border-line">
          <div className="text-xs font-mono text-ink-muted mb-2">Watchlist simbol</div>
          <div className="flex flex-wrap gap-2 mb-3">
            {liveSymbols.filter((s) => s.enabled).map((s) => (
              <span key={s.id} className="flex items-center gap-1.5 text-xs font-mono bg-raised border border-line rounded-full px-3 py-1">
                {s.symbol} · {s.timeframe}
                <button onClick={() => removeLiveSymbol(s.symbol, s.timeframe)} className="text-ink-faint hover:text-short">
                  <Trash2 size={11} />
                </button>
              </span>
            ))}
            {activeSymbols.length === 0 && <span className="text-xs text-ink-faint">Belum ada simbol di watchlist.</span>}
          </div>
          <div className="flex gap-2">
            <select value={newSymbolForm.symbol} onChange={(e) => setNewSymbolForm((f) => ({ ...f, symbol: e.target.value }))}
              className="bg-raised border border-line rounded-md px-2 py-1.5 text-xs font-mono focus-ring">
              {SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={newSymbolForm.timeframe} onChange={(e) => setNewSymbolForm((f) => ({ ...f, timeframe: e.target.value }))}
              className="bg-raised border border-line rounded-md px-2 py-1.5 text-xs font-mono focus-ring">
              {TIMEFRAMES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <button onClick={addLiveSymbol} disabled={busy}
              className="flex items-center gap-1 text-xs font-medium px-3 py-1.5 rounded-md border border-line text-ink-muted hover:border-amber hover:text-amber transition">
              <Plus size={12} /> Tambah
            </button>
          </div>
        </div>
      </div>

      {/* --- FORWARD TEST (paper, safe) --- */}
      <div className="panel p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Radio size={15} className="text-cyan" />
          <div className="text-sm font-semibold">Forward Test (paper, aman)</div>
        </div>
        <p className="text-xs text-ink-muted leading-relaxed">
          Logic sama persis kayak live auto-trade, pakai harga real-time, tapi order cuma
          dicatat — gak pernah kirim order asli. Cara paling aman buat lihat seberapa sering
          AI beneran nemuin sinyal sebelum kamu percaya nyalain live.
        </p>
        <div className="flex gap-2">
          <select value={ftForm.symbol} onChange={(e) => setFtForm((f) => ({ ...f, symbol: e.target.value }))}
            className="bg-raised border border-line rounded-md px-2 py-1.5 text-xs font-mono focus-ring">
            {SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={ftForm.timeframe} onChange={(e) => setFtForm((f) => ({ ...f, timeframe: e.target.value }))}
            className="bg-raised border border-line rounded-md px-2 py-1.5 text-xs font-mono focus-ring">
            {TIMEFRAMES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <button onClick={() => toggleForwardTest(true)} disabled={busy}
            className="text-xs font-semibold px-3 py-1.5 rounded-md border border-long/40 text-long bg-long/10 hover:bg-long/20 transition">
            Nyalakan
          </button>
          <button onClick={() => toggleForwardTest(false)} disabled={busy}
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-line text-ink-muted hover:border-short hover:text-short transition">
            Matikan
          </button>
        </div>

        {ftTrades.length > 0 && (
          <table className="w-full text-sm font-mono mt-2">
            <tbody>
              {ftTrades.slice(0, 8).map((t) => (
                <tr key={t.id} className="border-b border-line/50">
                  <td className="py-2">{t.symbol}</td>
                  <td className={t.direction === 'LONG' ? 'text-long' : 'text-short'}>{t.direction}</td>
                  <td className="text-ink-muted text-xs">{t.source}</td>
                  <td className={`text-right ${t.pnl_usd >= 0 ? 'text-long' : 'text-short'}`}>
                    {t.pnl_usd != null ? `${t.pnl_usd >= 0 ? '+' : ''}$${t.pnl_usd}` : 'open'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showConfirm && (
        <ConfirmModal
          title="Nyalakan Live Auto-Trade?"
          body={`AI bakal masang order ASLI pakai uang beneran di akun ${selected?.label} (${selected?.mt5_login}) tanpa kamu klik apa-apa, buat simbol: ${activeSymbols.map(s => s.symbol).join(', ')}. Ukuran lot ngikutin preset "${riskCfg.preset}" (margin ceiling ${riskCfg.max_margin_pct_per_trade}%). Kamu bisa matiin kapan aja lewat tombol Emergency Stop.`}
          confirmWord="AKTIFKAN"
          confirmLabel={busy ? 'Menyalakan…' : 'Ya, Nyalakan'}
          onConfirm={enableMaster}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </div>
  )
}
