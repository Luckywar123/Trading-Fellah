import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Crosshair, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { isWalletAvailable } from '../lib/wallet.js'

export default function Login() {
  const { login, error } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)

  const handleLogin = async () => {
    setBusy(true)
    try {
      await login()
      navigate('/')
    } catch {
      /* error sudah dipegang di AuthContext */
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-void text-ink flex items-center justify-center px-6 relative overflow-hidden">
      {/* ambient reticle rings — signature visual, quiet motion */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.07]">
        <svg width="900" height="900" viewBox="0 0 900 900">
          <circle cx="450" cy="450" r="420" fill="none" stroke="#F0A030" strokeWidth="1" />
          <circle cx="450" cy="450" r="320" fill="none" stroke="#F0A030" strokeWidth="1" />
          <circle cx="450" cy="450" r="220" fill="none" stroke="#F0A030" strokeWidth="1" />
          <line x1="450" y1="0" x2="450" y2="900" stroke="#F0A030" strokeWidth="1" />
          <line x1="0" y1="450" x2="900" y2="450" stroke="#F0A030" strokeWidth="1" />
        </svg>
      </div>

      <div className="relative w-full max-w-sm">
        <div className="flex items-center gap-2.5 justify-center mb-8">
          <Crosshair size={26} className="text-amber" strokeWidth={1.5} />
          <span className="font-display font-semibold text-lg tracking-tight">TRADING FELLAH</span>
        </div>

        <div className="panel scanline-edge p-7 text-center">
          <h1 className="font-display text-xl font-semibold mb-1.5">Masuk pakai wallet</h1>
          <p className="text-sm text-ink-muted mb-7 leading-relaxed">
            Gak ada email, gak ada password. Sign-in pakai wallet crypto kamu —
            tanda tangan pesan sekali, gratis, gak ada transaksi on-chain.
          </p>

          <button
            onClick={handleLogin}
            disabled={busy}
            className="w-full bg-amber text-void font-semibold text-sm rounded-md py-3 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60 focus-ring"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Crosshair size={16} />}
            {busy ? 'Menunggu tanda tangan…' : 'Connect Wallet'}
          </button>

          {!isWalletAvailable() && (
            <p className="mt-4 text-xs text-short leading-relaxed">
              Wallet extension gak terdeteksi. Install MetaMask (atau wallet EVM kompatibel
              lain) dulu di browser ini, terus refresh halaman.
            </p>
          )}
          {error && <p className="mt-4 text-xs text-short">{error}</p>}
        </div>

        <p className="text-center text-xs text-ink-faint mt-6 font-mono leading-relaxed">
          Trading forex/crypto pakai leverage berisiko tinggi.
          <br />Platform ini alat eksekusi, bukan nasihat finansial.
        </p>
      </div>
    </div>
  )
}
