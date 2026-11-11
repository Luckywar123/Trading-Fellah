import { BrowserProvider } from 'ethers'

/**
 * Login KHUSUS MetaMask. Kalau browser punya beberapa wallet extension
 * (Talisman, Rabby, Brave Wallet, dst), kita sengaja pilih provider MetaMask-nya
 * saja supaya gak rebutan `window.ethereum`.
 *
 * Deteksi: EIP-6963 (cara standar) dulu, fallback ke window.ethereum / providers[].
 */
const METAMASK_RDNS = ['io.metamask', 'io.metamask.flask']
export const METAMASK_INSTALL_URL = 'https://metamask.io/download/'

let announced = null // provider MetaMask dari EIP-6963
let active = null // provider yang dipakai di sesi connect ini

if (typeof window !== 'undefined') {
  window.addEventListener('eip6963:announceProvider', (e) => {
    const { info, provider } = e.detail || {}
    if (info && METAMASK_RDNS.includes(info.rdns) && provider) announced = provider
  })
  window.dispatchEvent(new Event('eip6963:requestProvider'))
}

function isRealMetaMask(p) {
  return !!p && p.isMetaMask === true &&
    !p.isTalisman && !p.isRabby && !p.isBraveWallet && !p.isCoinbaseWallet && !p.isPhantom && !p.isTrust
}

function getMetaMaskProvider() {
  if (typeof window === 'undefined') return null
  window.dispatchEvent(new Event('eip6963:requestProvider'))
  if (announced) return announced
  const eth = window.ethereum
  if (!eth) return null
  const list = Array.isArray(eth.providers) && eth.providers.length ? eth.providers : [eth]
  return list.find(isRealMetaMask) || null
}

export function isMetaMaskAvailable() {
  return !!getMetaMaskProvider()
}

export function isMobileBrowser() {
  return typeof navigator !== 'undefined' && /android|iphone|ipad|ipod/i.test(navigator.userAgent)
}

/** Buka situs ini di dalam browser bawaan app MetaMask (buat HP). */
export function metamaskMobileLink() {
  return `https://metamask.app.link/dapp/${window.location.host}${window.location.pathname}`
}

function friendly(e) {
  if (e && (e.code === 4001 || e.code === 'ACTION_REJECTED')) {
    return new Error('Kamu menolak permintaan di MetaMask. Coba lagi dan klik Sign/Connect.')
  }
  if (e && e.code === -32002) {
    return new Error('Ada permintaan MetaMask yang masih terbuka. Buka extension MetaMask dan selesaikan dulu.')
  }
  return e
}

export async function connectWallet() {
  const raw = getMetaMaskProvider()
  if (!raw) {
    throw new Error('MetaMask tidak terdeteksi. Install MetaMask dulu (atau nonaktifkan wallet lain), lalu refresh halaman.')
  }
  active = raw
  try {
    const provider = new BrowserProvider(raw)
    const accounts = await provider.send('eth_requestAccounts', [])
    return accounts[0]
  } catch (e) {
    throw friendly(e)
  }
}

export async function signMessage(message) {
  const raw = active || getMetaMaskProvider()
  if (!raw) throw new Error('MetaMask tidak terdeteksi.')
  try {
    const provider = new BrowserProvider(raw)
    const signer = await provider.getSigner()
    return await signer.signMessage(message)
  } catch (e) {
    throw friendly(e)
  }
}
