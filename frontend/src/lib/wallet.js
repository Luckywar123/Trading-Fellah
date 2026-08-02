import { BrowserProvider } from 'ethers'

/**
 * Login pakai wallet crypto (bukan email/password). Butuh extension wallet
 * yang inject `window.ethereum` (MetaMask, Rabby, Coinbase Wallet, dst).
 *
 * Catatan: ini pakai injected provider (cukup buat desktop browser). Kalau
 * nanti mau dukung scan QR dari mobile wallet juga, tambahkan WalletConnect
 * (butuh daftar project ID gratis di cloud.walletconnect.com) sebagai
 * provider kedua di sini — struktur function-nya (connectWallet / signMessage)
 * gak perlu berubah, tinggal tambah cabang provider.
 */
export function isWalletAvailable() {
  return typeof window !== 'undefined' && !!window.ethereum
}

export async function connectWallet() {
  if (!isWalletAvailable()) {
    throw new Error('Wallet extension tidak terdeteksi. Install MetaMask atau wallet kompatibel lainnya.')
  }
  const provider = new BrowserProvider(window.ethereum)
  const accounts = await provider.send('eth_requestAccounts', [])
  return accounts[0]
}

export async function signMessage(message) {
  const provider = new BrowserProvider(window.ethereum)
  const signer = await provider.getSigner()
  return signer.signMessage(message)
}
