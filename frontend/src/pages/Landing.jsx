import { useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Crosshair, Wallet, QrCode, Target, ShieldAlert, FlaskConical, Bot,
  Newspaper, Radar, Siren, ArrowRight, Check,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

const FEATURES = [
  {
    icon: Radar,
    title: 'AI Swing + Order Block Detector',
    body: 'Nyisir price action buat swing high/low, order block, dan support/resistance secara otomatis — bukan indikator lagging biasa.',
  },
  {
    icon: Target,
    title: 'Multi-broker MT5',
    body: 'Tautkan akun MT5 dari broker manapun. Eksekusi order, lihat balance & posisi real-time, semua dari satu dashboard.',
  },
  {
    icon: ShieldAlert,
    title: 'Risk Engine yang Bisa Kamu Atur',
    body: 'Preset dari Conservative sampai Full Send, ceiling margin per trade kamu sendiri yang tentuin. Gak ada yang dipaksain.',
  },
  {
    icon: Newspaper,
    title: 'News Sentiment AI',
    body: 'Auto-pause pas rilis berita high-impact, plus rationale AI di tiap sinyal biar kamu ngerti alasannya, bukan cuma ikut angka.',
  },
  {
    icon: FlaskConical,
    title: 'Backtest & Forward Test',
    body: 'Uji dulu logic-nya pakai data historis, terus jalanin paper trading dengan harga live sebelum berani ke akun real.',
  },
  {
    icon: Bot,
    title: 'Live Auto-Trade — Opt-in Berlapis',
    body: 'Master switch, watchlist per simbol, circuit breaker, sampai Emergency Stop satu tombol. Default-nya MATI sampai kamu aktifin sendiri.',
  },
]

const STEPS = [
  { title: 'Connect wallet', body: 'Sign-in pakai wallet crypto kamu — tanda tangan pesan sekali, gratis, gak ada transaksi on-chain, gak perlu email/password.' },
  { title: 'Tautkan akun MT5', body: 'Hubungkan akun MT5 broker kamu (demo dulu juga bisa) buat mulai eksplorasi sinyal dan backtest.' },
  { title: 'Atur risk, lalu jalan', body: 'Pilih preset risk, coba Forward Test beberapa hari, baru pertimbangkan nyalain live dengan preset kecil.' },
]

const PLANS = [
  { key: 'basic', name: 'Basic', price: 29, features: ['1 akun MT5', 'Manual trading + dashboard', 'Backtest terbatas'] },
  { key: 'pro', name: 'Pro', price: 79, features: ['3 akun MT5', 'AI swing/order block signals', 'Forward test', 'News sentiment AI'], highlight: true },
  { key: 'elite', name: 'Elite', price: 199, features: ['Akun MT5 tanpa batas', 'Full margin mode', 'Behavior profiling AI', 'Priority support'] },
]

export default function Landing() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && user) navigate('/dashboard', { replace: true })
  }, [user, loading, navigate])

  return (
    <div className="min-h-screen bg-void text-ink">
      {/* Top bar */}
      <header className="border-b border-line">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Crosshair size={22} className="text-amber" strokeWidth={1.5} />
            <span className="font-display font-semibold tracking-tight">TRADING FELLAH</span>
          </div>
          <Link
            to="/login"
            className="text-sm font-semibold bg-amber text-void rounded-md px-4 py-2 hover:brightness-110 transition focus-ring"
          >
            Connect Wallet
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.06]">
          <svg width="900" height="900" viewBox="0 0 900 900">
            <circle cx="450" cy="450" r="420" fill="none" stroke="#F0A030" strokeWidth="1" />
            <circle cx="450" cy="450" r="320" fill="none" stroke="#F0A030" strokeWidth="1" />
            <circle cx="450" cy="450" r="220" fill="none" stroke="#F0A030" strokeWidth="1" />
            <line x1="450" y1="0" x2="450" y2="900" stroke="#F0A030" strokeWidth="1" />
            <line x1="0" y1="450" x2="900" y2="450" stroke="#F0A030" strokeWidth="1" />
          </svg>
        </div>

        <div className="relative max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
          <div className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-amber font-mono border border-amber-dim/40 bg-amber-soft rounded-full px-3 py-1 mb-6">
            <Crosshair size={12} /> Sniper Terminal buat MT5
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tight leading-tight">
            Eksekusi trading MT5 kamu,<br className="hidden sm:block" /> dibantu AI yang jelasin alasannya.
          </h1>
          <p className="mt-5 text-ink-muted text-base leading-relaxed max-w-2xl mx-auto">
            Tautkan akun MT5 broker manapun, dapetin sinyal swing/order block/S&R dari AI,
            atur sendiri agresivitas risk-nya, dan uji dulu pakai backtest &amp; forward test
            sebelum berani ke akun live. Login pakai wallet, bukan email/password.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/login"
              className="w-full sm:w-auto bg-amber text-void font-semibold text-sm rounded-md px-6 py-3 flex items-center justify-center gap-2 hover:brightness-110 transition focus-ring"
            >
              <Wallet size={16} /> Connect Wallet &amp; Mulai
            </Link>
            <a
              href="#fitur"
              className="w-full sm:w-auto border border-line text-ink-muted text-sm rounded-md px-6 py-3 flex items-center justify-center gap-2 hover:bg-raised hover:text-ink transition"
            >
              Lihat fitur <ArrowRight size={14} />
            </a>
          </div>

          <p className="mt-8 text-xs text-ink-faint font-mono leading-relaxed max-w-xl mx-auto">
            Trading forex/crypto pakai leverage berisiko tinggi dan bisa bikin rugi modal.
            Platform ini alat eksekusi &amp; riset, bukan nasihat finansial — belum pernah
            divalidasi pakai data pasar asli, jalanin Forward Test dulu sebelum live.
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="fitur" className="border-t border-line">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <h2 className="font-display text-2xl font-semibold">Semua yang kamu butuh dalam satu dashboard</h2>
            <p className="text-sm text-ink-muted mt-2">Dari deteksi sinyal sampai lapisan pengaman auto-trade.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <div key={title} className="panel p-5">
                <Icon size={20} className="text-amber mb-3" strokeWidth={1.75} />
                <h3 className="font-display font-semibold text-sm mb-1.5">{title}</h3>
                <p className="text-xs text-ink-muted leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-line">
        <div className="max-w-4xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <h2 className="font-display text-2xl font-semibold">Cara mulai</h2>
            <p className="text-sm text-ink-muted mt-2">Tiga langkah, gak ada yang ribet.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {STEPS.map((s, i) => (
              <div key={s.title} className="panel p-5">
                <div className="w-7 h-7 rounded-full bg-amber-soft border border-amber-dim/40 text-amber font-mono text-xs flex items-center justify-center mb-3">
                  {i + 1}
                </div>
                <h3 className="font-display font-semibold text-sm mb-1.5">{s.title}</h3>
                <p className="text-xs text-ink-muted leading-relaxed">{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Safety layers */}
      <section className="border-t border-line">
        <div className="max-w-4xl mx-auto px-6 py-16">
          <div className="panel p-6 sm:p-8">
            <div className="flex items-center gap-2 mb-4">
              <Siren size={18} className="text-short" />
              <h2 className="font-display text-lg font-semibold">Auto-trade default-nya MATI</h2>
            </div>
            <p className="text-sm text-ink-muted leading-relaxed mb-4">
              Live auto-trade cuma nyala kalau kamu aktifin sendiri lewat konfirmasi eksplisit — dan
              tetap dijaga berlapis:
            </p>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm text-ink-muted">
              {[
                'Master switch per akun MT5, default OFF',
                'Watchlist simbol yang kamu pilih sendiri',
                'News blackout net pas rilis high-impact',
                'Circuit breaker: 5 loss beruntun / drawdown 20%',
                'Emergency Stop satu tombol, permanen di topbar',
                'Ambang confidence AI sebelum eksekusi',
              ].map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <Check size={14} className="text-long shrink-0 mt-0.5" /> {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="border-t border-line">
        <div className="max-w-5xl mx-auto px-6 py-16">
          <div className="text-center mb-10">
            <h2 className="font-display text-2xl font-semibold">Membership</h2>
            <p className="text-sm text-ink-muted mt-2">
              Bayar pakai crypto (BTC/ETH/USDT/dll) atau QRIS — GoPay, OVO, DANA, ShopeePay, m-banking.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PLANS.map((p) => (
              <div key={p.key} className={`panel p-5 flex flex-col ${p.highlight ? 'border-amber' : ''}`}>
                {p.highlight && (
                  <div className="text-[10px] uppercase tracking-widest text-amber font-mono mb-2">Paling populer</div>
                )}
                <div className="text-sm font-semibold text-ink-muted uppercase tracking-wide">{p.name}</div>
                <div className="mt-2 font-display text-3xl font-semibold">${p.price}<span className="text-sm text-ink-faint font-body">/bulan</span></div>
                <ul className="mt-4 space-y-2 flex-1">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-ink-muted">
                      <Check size={13} className="text-long shrink-0 mt-0.5" /> {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/login"
                  className="mt-5 w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:brightness-110 transition"
                >
                  Mulai
                </Link>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-6 mt-8 text-xs text-ink-faint">
            <span className="flex items-center gap-1.5"><Wallet size={13} /> Crypto wallet</span>
            <span className="flex items-center gap-1.5"><QrCode size={13} /> QRIS</span>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="border-t border-line">
        <div className="max-w-2xl mx-auto px-6 py-16 text-center">
          <h2 className="font-display text-2xl font-semibold mb-3">Siap coba?</h2>
          <p className="text-sm text-ink-muted mb-6">
            Connect wallet, tautkan MT5 demo, dan lihat sendiri sinyalnya sebelum mikirin live.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 bg-amber text-void font-semibold text-sm rounded-md px-6 py-3 hover:brightness-110 transition"
          >
            <Wallet size={16} /> Connect Wallet
          </Link>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="max-w-6xl mx-auto px-6 py-8 text-center text-xs text-ink-faint font-mono">
          Trading forex/crypto pakai leverage berisiko tinggi. Platform ini alat eksekusi, bukan nasihat finansial.
        </div>
      </footer>
    </div>
  )
}
