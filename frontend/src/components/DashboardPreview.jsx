import { Lock } from 'lucide-react'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import StatCard from './StatCard.jsx'
import MetaMaskButton from './MetaMaskButton.jsx'

// Data CONTOH (statis) — bukan akun asli siapa pun. Dashboard asli muncul setelah login.
const CURVE = [
  { t: 'Sen', equity: 10000 }, { t: 'Sel', equity: 10120 }, { t: 'Rab', equity: 10060 },
  { t: 'Kam', equity: 10240 }, { t: 'Jum', equity: 10190 }, { t: 'Sab', equity: 10380 },
  { t: 'Min', equity: 10460 },
]
const POSITIONS = [
  { sym: 'XAUUSD', side: 'BUY', lot: '0.10', pnl: '+$42.10' },
  { sym: 'EURUSD', side: 'SELL', lot: '0.20', pnl: '-$11.40' },
  { sym: 'BTCUSD', side: 'BUY', lot: '0.02', pnl: '+$27.85' },
]

export default function DashboardPreview() {
  return (
    <section className="max-w-6xl mx-auto px-6 pt-8 pb-12">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h1 className="font-display text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-ink-muted mt-1">
            Gambaran tampilan setelah login. Login pakai MetaMask buat nautin akun MT5 kamu sendiri.
          </p>
        </div>
        <span className="text-[11px] uppercase tracking-[0.15em] font-mono text-amber border border-amber-dim/40 bg-amber-soft rounded-full px-3 py-1">
          Preview · data contoh
        </span>
      </div>

      <div className="relative">
        <div className="space-y-4 pointer-events-none select-none" aria-hidden="true">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Balance" value="$10,000.00" sub="Akun demo" />
            <StatCard label="Equity" value="$10,460.55" tone="amber" sub="+4.61% minggu ini" />
            <StatCard label="Floating P/L" value="+$58.55" tone="positive" sub="3 posisi terbuka" />
            <StatCard label="Margin Level" value="1,842%" sub="Aman" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="panel p-5 lg:col-span-2">
              <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Equity Curve</div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={CURVE}>
                  <defs>
                    <linearGradient id="eqp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F0A030" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#F0A030" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#2A3035" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="t" stroke="#5A6166" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
                  <YAxis stroke="#5A6166" tick={{ fontSize: 11, fontFamily: 'IBM Plex Mono' }} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ background: '#1E2327', border: '1px solid #2A3035', borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="equity" stroke="#F0A030" fill="url(#eqp)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="panel p-5">
              <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Posisi Terbuka</div>
              <table className="w-full text-sm font-mono">
                <tbody>
                  {POSITIONS.map((p) => (
                    <tr key={p.sym} className="border-b border-line/50">
                      <td className="py-2">{p.sym}</td>
                      <td className={p.side === 'BUY' ? 'text-long' : 'text-short'}>{p.side}</td>
                      <td className="text-ink-muted">{p.lot}</td>
                      <td className={`text-right ${p.pnl.startsWith('+') ? 'text-long' : 'text-short'}`}>{p.pnl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* overlay ajakan login */}
        <div className="absolute inset-0 flex items-center justify-center bg-void/55 backdrop-blur-[2px] rounded-lg">
          <div className="panel p-6 text-center max-w-sm mx-4">
            <Lock size={20} className="text-amber mx-auto mb-2" />
            <div className="font-display font-semibold mb-1">Data akun kamu ada di balik login</div>
            <p className="text-xs text-ink-muted mb-4 leading-relaxed">
              Cukup tanda tangan pesan di MetaMask. Gratis, tanpa transaksi on-chain, tanpa email/password.
            </p>
            <MetaMaskButton className="w-full" />
          </div>
        </div>
      </div>
    </section>
  )
}
