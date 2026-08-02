import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from '../lib/api.js'
import { connectWallet, signMessage } from '../lib/wallet.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const bootstrap = useCallback(async () => {
    const token = localStorage.getItem('tf_token')
    if (!token) {
      setLoading(false)
      return
    }
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      localStorage.removeItem('tf_token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  const login = useCallback(async () => {
    setError(null)
    try {
      const wallet = await connectWallet()
      const { message } = await api.requestNonce(wallet)
      const signature = await signMessage(message)
      const { token, user: loggedInUser } = await api.verify(wallet, signature)
      localStorage.setItem('tf_token', token)
      setUser(loggedInUser)
      return loggedInUser
    } catch (e) {
      setError(e.message || 'Login gagal')
      throw e
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('tf_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
