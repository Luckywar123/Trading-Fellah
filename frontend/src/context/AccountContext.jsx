import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../lib/api.js'
import { useAuth } from './AuthContext.jsx'

const AccountContext = createContext(null)

export function AccountProvider({ children }) {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!user) return
    setLoading(true)
    try {
      const list = await api.listAccounts()
      setAccounts(list)
      setSelectedId((prev) => prev && list.some((a) => a.id === prev) ? prev : list[0]?.id ?? null)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) refresh()
    else {
      setAccounts([])
      setSelectedId(null)
      setLoading(false)
    }
  }, [user, refresh])

  const selected = accounts.find((a) => a.id === selectedId) || null

  return (
    <AccountContext.Provider value={{ accounts, selected, selectedId, setSelectedId, refresh, loading }}>
      {children}
    </AccountContext.Provider>
  )
}

export function useAccounts() {
  const ctx = useContext(AccountContext)
  if (!ctx) throw new Error('useAccounts must be used inside AccountProvider')
  return ctx
}
