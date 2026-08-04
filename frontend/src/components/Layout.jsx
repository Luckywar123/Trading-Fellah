import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import {
  Crosshair, LayoutGrid, Target, ShieldAlert, FlaskConical, Bot, Newspaper, Wallet, LogOut,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useAccounts } from '../context/AccountContext.jsx'
import { api } from '../lib/api.js'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid },
  { to: '/trade', label: 'Trade', icon: Target },
  { to: '/risk', label: 'Risk Settings', icon: ShieldAlert },
  { to: '/backtest', label: 'Backtest', icon: FlaskConical },
  { to: '/automation', label: 'Automation', icon: Bot },
  { to: '/ai', label: 'AI Insights', icon: Newspaper },
  { to: '/billing', label: 'Billing', icon: Wallet },
]

function shortAddr(addr) {
  if (!addr) return ''
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`
}

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { accounts, selectedId, setSelectedId, selected } = useAccounts()
  const navigate = useNavigate()
  const [liveOn, setLiveOn] = useState(false)
  const [stopping, setStopping] = useState(false)

  const checkLiveStatus = useCallback(async () => {
    if (!selectedId) { setLiveOn(false); return }
    try {
      const risk = await api.getRiskSettings(selectedId)
      setLiveOn(!!risk.live_autotrade_enabled)
    } catch {
      setLiveOn(false)
    }
  }, [selectedId])

  useEffect(() => {
    checkLiveStatus()
    const t = setInterval(checkLiveStatus, 20000)
    return () => clearInterval(t)
  }, [checkLiveStatus])

  const handleEmergencyStop = async () => {
    if (!selectedId) return
    if (!window.confirm('Matiin auto-trade DAN tutup semua posisi terbuka di akun ini sekarang?')) return
    setStopping(true)
    try {
      await api.emergencyStop(selectedId)
      setLiveOn(false)
      navigate('/automation')
    } finally {
      setStopping(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-void text-ink">
      {/* Sidebar */}
      <aside className="w-60 shrink-0 border-r border-line flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-line">
          <Crosshair size={20} className="text-amber" strokeWidth={1.75} />
          <span className="font-display font-semibold tracking-tight text-[15px]">TRADING FELLAH</span>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-ring ${
                  isActive
                    ? 'bg-amber-soft text-amber border border-amber-dim/40'
                    : 'text-ink-muted hover:text-ink hover:bg-raised'
                }`
              }
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-line space-y-2">
          <div className="text-[10px] uppercase tracking-widest text-ink-faint font-mono px-1">Wallet</div>
          <div className="px-1 text-sm font-mono text-ink-muted">{shortAddr(user?.wallet_address)}</div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-ink-muted hover:text-short hover:bg-raised transition-colors focus-ring"
          >
            <LogOut size={15} strokeWidth={1.75} />
            Keluar
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-line flex items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-widest text-ink-faint font-mono">Akun Aktif</span>
            <select
              value={selectedId || ''}
              onChange={(e) => setSelectedId(e.target.value)}
              className="bg-raised border border-line rounded-md px-3 py-1.5 text-sm font-mono focus-ring"
            >
              {accounts.length === 0 && <option value="">Belum ada akun ditautkan</option>}
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label} · {a.mt5_login} {a.is_live ? '(LIVE)' : '(DEMO)'}
                </option>
              ))}
            </select>
          </div>
          {selected && (
            <div className="flex items-center gap-3">
              {liveOn && (
                <button
                  onClick={handleEmergencyStop}
                  disabled={stopping}
                  className="text-xs font-mono font-semibold px-3 py-1.5 rounded-full bg-short text-void animate-pulse hover:brightness-110 transition disabled:opacity-60"
                >
                  🛑 {stopping ? 'Menghentikan…' : 'LIVE AUTO-TRADE — STOP'}
                </button>
              )}
              <span
                className={`text-xs font-mono px-2.5 py-1 rounded-full border ${
                  selected.connection_status === 'connected'
                    ? 'border-long/40 text-long bg-long/10'
                    : 'border-short/40 text-short bg-short/10'
                }`}
              >
                ● {selected.connection_status?.toUpperCase()}
              </span>
            </div>
          )}
        </header>
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
