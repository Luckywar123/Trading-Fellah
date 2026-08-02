import { useEffect, useState, useCallback } from 'react'
import { Loader2, X } from 'lucide-react'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'
import LinkAccountForm from '../components/LinkAccountForm.jsx'

const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AUDUSD', 'USDCAD', 'BTCUSD']

export default function Trade() {
  const { selected, accounts } = useAccounts()
  const [positions, setPositions] = useState([])
  const [form, setForm] = useState({ symbol: 'EURUSD', direction: 'LONG', stop_loss: '', take_profit: '', volume_lots: '' })
  const [busy, setBusy] = useState(false)
  const [closingTicket, setClosingTicket] = useState(null)
  const [msg, setMsg] = useState(null)

  const loadPositions = useCallback(async () => {
    if (!selected) return
    try {
      setPositions(await api.getPositions(selected.id))
    } catch { /* ignore transient */ }
  }, [selected])

  useEffect(() => {
    loadPositions()
    const t = setInterval(loadPositions, 10000)
    return () => clearInterval(t)
  }, [loadPositions])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      const payload = {
        symbol: form.symbol, direction: form.direction, comment: 'manual-ui',
        stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
        take_profit: form.take_profit ? parseFloat(form.take_profit) : null,
        volume_lots: form.volume_lots ? parseFloat(form.volume_lots) : null,
      }
      await api.openOrder(selected.id, payload)
      setMsg({ type: 'ok', text: 'Order berhasil dibuka.' })
      loadPositions()
    } catch (e2) {
      setMsg({ type: 'err', text: e2.message })
    } finally {
      setBusy(false)
    }
  }

  const close = async (ticket) => {
    setClosingTicket(ticket)
    try {
      await api.closeOrder(selected.id, ticket)
      loadPositions()
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setClosingTicket(null)
    }
  }

  if (accounts.length === 0) {
    return <LinkAccountForm />
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="panel p-5 h-fit">
        <h2 className="font-display text-base font-semibold mb-4">Buka Order</h2>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-xs text-ink-muted font-mono">Symbol</label>
            <select value={form.symbol} onChange={set('symbol')} className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring">
              {SYMBOLS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setForm((f) => ({ ...f, direction: 'LONG' }))}
              className={`py-2.5 rounded-md text-sm font-semibold border transition ${form.direction === 'LONG' ? 'bg-long/15 border-long text-long' : 'border-line text-ink-muted'}`}>
              LONG
            </button>
            <button type="button" onClick={() => setForm((f) => ({ ...f, direction: 'SHORT' }))}
              className={`py-2.5 rounded-md text-sm font-semibold border transition ${form.direction === 'SHORT' ? 'bg-short/15 border-short text-short' : 'border-line text-ink-muted'}`}>
              SHORT
            </button>
          </div>

          <div>
            <label className="text-xs text-ink-muted font-mono">Stop Loss (harga)</label>
            <input value={form.stop_loss} onChange={set('stop_loss')} placeholder="wajib diisi buat auto lot-size"
              className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring" />
          </div>
          <div>
            <label className="text-xs text-ink-muted font-mono">Take Profit (harga, opsional)</label>
            <input value={form.take_profit} onChange={set('take_profit')}
              className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring" />
          </div>
          <div>
            <label className="text-xs text-ink-muted font-mono">Volume (lot) — kosongkan buat auto-size dari Risk Settings</label>
            <input value={form.volume_lots} onChange={set('volume_lots')} placeholder="auto"
              className="w-full mt-1 bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring" />
          </div>

          {msg && <p className={`text-xs ${msg.type === 'ok' ? 'text-long' : 'text-short'}`}>{msg.text}</p>}

          <button type="submit" disabled={busy}
            className="w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60">
            {busy && <Loader2 size={14} className="animate-spin" />}
            {busy ? 'Mengirim order…' : `Eksekusi ${form.direction}`}
          </button>
          <p className="text-[11px] text-ink-faint leading-relaxed">
            Ukuran lot & margin dihitung otomatis pakai preset Risk Settings kamu
            (termasuk news blackout gate & ceiling margin per-order).
          </p>
        </form>
      </div>

      <div className="lg:col-span-2 panel p-5">
        <h2 className="font-display text-base font-semibold mb-4">Posisi Terbuka ({positions.length})</h2>
        {positions.length === 0 ? (
          <p className="text-sm text-ink-faint py-6 text-center">Belum ada posisi terbuka.</p>
        ) : (
          <div className="space-y-2">
            {positions.map((p) => (
              <div key={p.ticket} className="flex items-center justify-between bg-raised border border-line rounded-lg px-4 py-3">
                <div className="flex items-center gap-4 font-mono text-sm">
                  <span className="font-semibold w-20">{p.symbol}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${p.direction === 'LONG' ? 'bg-long/15 text-long' : 'bg-short/15 text-short'}`}>{p.direction}</span>
                  <span className="text-ink-muted">{p.volume} lot</span>
                  <span className="text-ink-muted">@ {p.open_price}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`font-mono text-sm ${p.profit >= 0 ? 'text-long' : 'text-short'}`}>
                    {p.profit >= 0 ? '+' : ''}${p.profit?.toFixed(2)}
                  </span>
                  <button onClick={() => close(p.ticket)} disabled={closingTicket === p.ticket}
                    className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md border border-line text-ink-muted hover:border-short hover:text-short transition disabled:opacity-50">
                    {closingTicket === p.ticket ? <Loader2 size={12} className="animate-spin" /> : <X size={12} />}
                    Close
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
