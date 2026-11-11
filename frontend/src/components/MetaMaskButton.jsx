import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Wallet } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import {
  isMetaMaskAvailable, isMobileBrowser, metamaskMobileLink, METAMASK_INSTALL_URL,
} from '../lib/wallet.js'

/**
 * Tombol login MetaMask yang dipakai di mana aja (header, preview, pricing).
 * Klik -> connect + sign pesan -> masuk ke /dashboard.
 */
export default function MetaMaskButton({
  label = 'Login dengan MetaMask',
  className = '',
  showHelp = true,
}) {
  const { login, error } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [missing, setMissing] = useState(false)

  const handle = async () => {
    if (!isMetaMaskAvailable()) {
      setMissing(true)
      if (isMobileBrowser()) window.location.href = metamaskMobileLink()
      return
    }
    setMissing(false)
    setBusy(true)
    try {
      await login()
      navigate('/dashboard')
    } catch {
      /* pesan error sudah dipegang AuthContext */
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="inline-flex flex-col items-end">
      <button
        onClick={handle}
        disabled={busy}
        className={`bg-amber text-void font-semibold text-sm rounded-md px-4 py-2 flex items-center justify-center gap-2 hover:brightness-110 transition disabled:opacity-60 focus-ring ${className}`}
      >
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Wallet size={15} />}
        {busy ? 'Menunggu MetaMask…' : label}
      </button>
      {showHelp && missing && !isMobileBrowser() && (
        <p className="mt-2 text-xs text-short max-w-[260px] text-right leading-relaxed">
          MetaMask belum terdeteksi.{' '}
          <a className="underline" href={METAMASK_INSTALL_URL} target="_blank" rel="noreferrer">Install MetaMask</a>
          , lalu refresh halaman ini.
        </p>
      )}
      {showHelp && error && !missing && (
        <p className="mt-2 text-xs text-short max-w-[260px] text-right leading-relaxed">{error}</p>
      )}
    </div>
  )
}
