import { useEffect, useState } from 'react'
import { Check, Loader2, Wallet, QrCode } from 'lucide-react'
import { api } from '../lib/api.js'
import QrisModal from '../components/QrisModal.jsx'

const PLANS = [
  { key: 'basic', name: 'Basic', price: 29, features: ['1 akun MT5', 'Manual trading + dashboard', 'Backtest terbatas'] },
  { key: 'pro', name: 'Pro', price: 79, features: ['3 akun MT5', 'AI swing/order block signals', 'Forward test', 'News sentiment AI'] },
  { key: 'elite', name: 'Elite', price: 199, features: ['Akun MT5 tanpa batas', 'Full margin mode', 'Behavior profiling AI', 'Priority support'] },
]

function formatIDR(n) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n)
}

export default function Billing() {
  const [status, setStatus] = useState(null)
  const [payments, setPayments] = useState([])
  const [busy, setBusy] = useState(null) // `${plan}:${method}` pas lagi proses
  const [err, setErr] = useState(null)
  const [qrisCharge, setQrisCharge] = useState(null)

  const refresh = () => {
    api.billingStatus().then(setStatus).catch(() => {})
    api.payments().then(setPayments).catch(() => {})
  }

  useEffect(refresh, [])

  const payWithCrypto = async (plan) => {
    setBusy(`${plan}:crypto`)
    setErr(null)
    try {
      const { invoice_url } = await api.checkout({
        plan,
        success_url: `${window.location.origin}/billing?status=success`,
        cancel_url: `${window.location.origin}/billing?status=cancelled`,
      })
      window.location.href = invoice_url
    } catch (e) {
      setErr(e.message)
      setBusy(null)
    }
  }

  const payWithQris = async (plan) => {
    setBusy(`${plan}:qris`)
    setErr(null)
    try {
      const charge = await api.checkoutQris({ plan })
      setQrisCharge(charge)
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="font-display text-xl font-semibold flex items-center gap-2">
          <Wallet size={20} className="text-amber" /> Membership
        </h1>
        <p className="text-sm text-ink-muted mt-1">
          Status sekarang: <span className={`font-semibold ${status?.status === 'active' ? 'text-long' : 'text-short'}`}>
            {status?.status?.toUpperCase() ?? '...'}
          </span>
          {status?.plan && <> · Plan {status.plan.toUpperCase()}</>}
          {status?.current_period_end && <> · Berlaku sampai {new Date(status.current_period_end).toLocaleDateString('id-ID')}</>}
        </p>
      </div>

      {err && <div className="panel border-short/40 bg-short/10 p-3 text-sm text-short">{err}</div>}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {PLANS.map((p) => (
          <div key={p.key} className={`panel p-5 flex flex-col ${status?.plan === p.key && status?.status === 'active' ? 'border-amber' : ''}`}>
            <div className="text-sm font-semibold text-ink-muted uppercase tracking-wide">{p.name}</div>
            <div className="mt-2 font-display text-3xl font-semibold">${p.price}<span className="text-sm text-ink-faint font-body">/bulan</span></div>
            <ul className="mt-4 space-y-2 flex-1">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-xs text-ink-muted">
                  <Check size={13} className="text-long shrink-0 mt-0.5" /> {f}
                </li>
              ))}
            </ul>

            <div className="mt-5 space-y-2">
              <button
                onClick={() => payWithCrypto(p.key)}
                disabled={busy !== null}
                className="w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60"
              >
                {busy === `${p.key}:crypto` ? <Loader2 size={14} className="animate-spin" /> : <Wallet size={14} />}
                {busy === `${p.key}:crypto` ? 'Membuat invoice…' : 'Bayar Crypto'}
              </button>
              <button
                onClick={() => payWithQris(p.key)}
                disabled={busy !== null}
                className="w-full border border-line text-ink font-semibold text-sm rounded-md py-2.5 flex items-center justify-center gap-2 hover:bg-raised transition disabled:opacity-60"
              >
                {busy === `${p.key}:qris` ? <Loader2 size={14} className="animate-spin" /> : <QrCode size={14} />}
                {busy === `${p.key}:qris` ? 'Menyiapkan QR…' : 'Bayar QRIS'}
              </button>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-ink-faint">
        <strong>Crypto</strong>: diproses NOWPayments — diarahkan ke halaman checkout mereka, pilih koin
        (BTC/ETH/USDT/dll), scan/kirim ke alamat yang diberikan. <strong>QRIS</strong>: scan langsung dari
        GoPay/OVO/DANA/ShopeePay/m-banking. Kedua metode aktifin membership otomatis begitu pembayaran confirmed.
      </p>

      <div className="panel p-5">
        <div className="text-[11px] uppercase tracking-[0.15em] text-ink-muted font-mono mb-3">Riwayat Pembayaran</div>
        {payments.length === 0 ? (
          <p className="text-sm text-ink-faint py-4">Belum ada riwayat pembayaran.</p>
        ) : (
          <table className="w-full text-sm font-mono">
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-b border-line/50">
                  <td className="py-2">{p.plan?.toUpperCase()}</td>
                  <td className="text-ink-muted">{p.pay_currency === 'QRIS' ? formatIDR(p.amount_usd) : `$${p.amount_usd}`}</td>
                  <td className="text-ink-muted">{p.pay_currency || '-'}</td>
                  <td className={p.status === 'finished' ? 'text-long' : 'text-ink-muted'}>{p.status}</td>
                  <td className="text-ink-faint text-xs">{new Date(p.created_at).toLocaleString('id-ID')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {qrisCharge && (
        <QrisModal
          charge={qrisCharge}
          onClose={() => { setQrisCharge(null); refresh() }}
          onPaid={refresh}
        />
      )}
    </div>
  )
}
