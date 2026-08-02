import { useState } from 'react'
import { Loader2, Plug } from 'lucide-react'
import { api } from '../lib/api.js'
import { useAccounts } from '../context/AccountContext.jsx'

export default function LinkAccountForm({ onDone }) {
  const { refresh } = useAccounts()
  const [form, setForm] = useState({
    label: '', broker_server: '', mt5_login: '', mt5_password: '', is_live: false,
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      await api.linkAccount({ ...form, label: form.label || 'Main Account' })
      await refresh()
      onDone?.()
    } catch (e2) {
      setErr(e2.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="panel p-5 space-y-3 max-w-md">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink mb-1">
        <Plug size={16} className="text-amber" />
        Tautkan akun MT5
      </div>
      <p className="text-xs text-ink-muted leading-relaxed mb-2">
        Bisa broker MT5 apa aja — isi persis nomor login, password, dan nama server
        broker kamu (contoh: <span className="font-mono">VantageInternational-Live 3</span>).
        Password dienkripsi sebelum disimpan.
      </p>

      <input
        placeholder="Label (contoh: Akun Utama)" value={form.label} onChange={set('label')}
        className="w-full bg-raised border border-line rounded-md px-3 py-2 text-sm focus-ring"
      />
      <input
        placeholder="Nama server broker" value={form.broker_server} onChange={set('broker_server')} required
        className="w-full bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring"
      />
      <input
        placeholder="Nomor login MT5" value={form.mt5_login} onChange={set('mt5_login')} required
        className="w-full bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring"
      />
      <input
        placeholder="Password MT5" type="password" value={form.mt5_password} onChange={set('mt5_password')} required
        className="w-full bg-raised border border-line rounded-md px-3 py-2 text-sm font-mono focus-ring"
      />
      <label className="flex items-center gap-2 text-xs text-ink-muted">
        <input type="checkbox" checked={form.is_live} onChange={set('is_live')} />
        Ini akun LIVE (bukan demo)
      </label>

      {err && <p className="text-xs text-short">{err}</p>}

      <button
        type="submit" disabled={busy}
        className="w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60"
      >
        {busy && <Loader2 size={14} className="animate-spin" />}
        {busy ? 'Menghubungkan ke MT5…' : 'Hubungkan Akun'}
      </button>
    </form>
  )
}
