import { useEffect, useRef, useState } from 'react'
import { X, Loader2, CheckCircle2, RefreshCw } from 'lucide-react'
import { api } from '../lib/api.js'

function formatIDR(n) {
  return new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', maximumFractionDigits: 0 }).format(n)
}

export default function QrisModal({ charge, onClose, onPaid }) {
  const [status, setStatus] = useState('waiting') // waiting | finished | expired | failed
  const [secondsLeft, setSecondsLeft] = useState(charge.expiry_minutes * 60)
  const pollRef = useRef(null)

  useEffect(() => {
    const tick = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000)
    return () => clearInterval(tick)
  }, [])

  useEffect(() => {
    if (secondsLeft === 0 && status === 'waiting') setStatus('expired')
  }, [secondsLeft, status])

  const checkStatus = async () => {
    try {
      const res = await api.qrisStatus(charge.order_id)
      if (res.status === 'finished') {
        setStatus('finished')
        onPaid?.()
      } else if (res.status === 'expired' || res.status === 'failed') {
        setStatus(res.status)
      }
    } catch {
      /* biarin, coba lagi di polling berikutnya */
    }
  }

  useEffect(() => {
    if (status !== 'waiting') return
    pollRef.current = setInterval(checkStatus, 5000)
    return () => clearInterval(pollRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status])

  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, '0')
  const ss = String(secondsLeft % 60).padStart(2, '0')

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="panel max-w-sm w-full p-6 text-center relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-ink-faint hover:text-ink">
          <X size={18} />
        </button>

        <h3 className="font-display font-semibold text-base mb-1">Scan QRIS buat bayar</h3>
        <p className="text-xs text-ink-muted mb-4">
          Bisa pakai GoPay, OVO, DANA, ShopeePay, atau m-banking mana aja yang support QRIS.
        </p>

        {status === 'waiting' && (
          <>
            <div className="bg-white rounded-lg p-3 mx-auto w-fit mb-4">
              <img src={charge.qr_image_url} alt="QRIS code" className="w-52 h-52" />
            </div>
            <div className="font-display text-2xl font-semibold mb-1">{formatIDR(charge.gross_amount)}</div>
            <div className="text-xs text-ink-faint font-mono mb-4">
              Berlaku {mm}:{ss} lagi
            </div>
            <button
              onClick={checkStatus}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium border border-line text-ink-muted hover:bg-raised transition"
            >
              <RefreshCw size={14} /> Cek status pembayaran
            </button>
            <p className="text-[11px] text-ink-faint mt-3 flex items-center justify-center gap-1.5">
              <Loader2 size={12} className="animate-spin" /> Nunggu konfirmasi otomatis…
            </p>
          </>
        )}

        {status === 'finished' && (
          <div className="py-6">
            <CheckCircle2 size={40} className="text-long mx-auto mb-3" />
            <p className="text-sm font-semibold">Pembayaran diterima</p>
            <p className="text-xs text-ink-muted mt-1">Membership kamu udah aktif.</p>
            <button onClick={onClose} className="mt-5 w-full bg-amber text-void font-semibold text-sm rounded-md py-2.5">
              Selesai
            </button>
          </div>
        )}

        {(status === 'expired' || status === 'failed') && (
          <div className="py-6">
            <p className="text-sm font-semibold text-short">
              {status === 'expired' ? 'QR code kadaluarsa' : 'Pembayaran gagal'}
            </p>
            <p className="text-xs text-ink-muted mt-1">Tutup, lalu coba checkout QRIS lagi.</p>
            <button onClick={onClose} className="mt-5 w-full border border-line rounded-md py-2.5 text-sm">
              Tutup
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
