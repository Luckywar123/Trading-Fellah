const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('tf_token')
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth) {
    const token = getToken()
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      /* body wasn't json */
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // --- auth ---
  requestNonce: (wallet) => request('/api/auth/nonce', { method: 'POST', body: { wallet }, auth: false }),
  verify: (wallet, signature) =>
    request('/api/auth/verify', { method: 'POST', body: { wallet, signature }, auth: false }),
  me: () => request('/api/auth/me'),

  // --- mt5 accounts ---
  listAccounts: () => request('/api/mt5/accounts'),
  linkAccount: (payload) => request('/api/mt5/accounts', { method: 'POST', body: payload }),
  unlinkAccount: (id) => request(`/api/mt5/accounts/${id}`, { method: 'DELETE' }),
  getBalance: (id) => request(`/api/mt5/accounts/${id}/balance`),
  getPositions: (id) => request(`/api/mt5/accounts/${id}/positions`),

  // --- trading ---
  openOrder: (accountId, payload) => request(`/api/trading/accounts/${accountId}/open`, { method: 'POST', body: payload }),
  closeOrder: (accountId, ticket) => request(`/api/trading/accounts/${accountId}/close/${ticket}`, { method: 'POST' }),
  history: (accountId) => request(`/api/trading/accounts/${accountId}/history`),
  emergencyStop: (accountId) => request(`/api/trading/accounts/${accountId}/emergency-stop`, { method: 'POST' }),
  listAutotradeSymbols: (accountId) => request(`/api/trading/accounts/${accountId}/autotrade/symbols`),
  toggleAutotradeSymbol: (accountId, payload) =>
    request(`/api/trading/accounts/${accountId}/autotrade/symbols`, { method: 'POST', body: payload }),

  // --- risk ---
  presets: () => request('/api/risk/presets'),
  getRiskSettings: (accountId) => request(`/api/risk/accounts/${accountId}/settings`),
  updateRiskSettings: (accountId, payload) =>
    request(`/api/risk/accounts/${accountId}/settings`, { method: 'PUT', body: payload }),

  // --- backtest / forward test ---
  runBacktest: (payload) => request('/api/backtest/run', { method: 'POST', body: payload }),
  getBacktest: (id) => request(`/api/backtest/${id}`),
  listBacktests: () => request('/api/backtest'),
  toggleForwardTest: (accountId, payload) =>
    request(`/api/backtest/forward-test/accounts/${accountId}/toggle`, { method: 'POST', body: payload }),
  forwardTestTrades: (accountId) => request(`/api/backtest/forward-test/accounts/${accountId}/trades`),

  // --- ai ---
  news: () => request('/api/ai/news'),
  refreshNews: () => request('/api/ai/news/refresh', { method: 'POST' }),
  blackoutStatus: () => request('/api/ai/news/blackout-status', { auth: false }),
  generateBehavior: (accountId) => request(`/api/ai/behavior/accounts/${accountId}/generate`, { method: 'POST' }),
  latestBehavior: () => request('/api/ai/behavior/latest'),
  listKnowledge: () => request('/api/ai/knowledge'),
  addKnowledge: (payload) => request('/api/ai/knowledge', { method: 'POST', body: payload }),

  // --- billing ---
  billingStatus: () => request('/api/billing/status'),
  checkout: (payload) => request('/api/billing/checkout', { method: 'POST', body: payload }),
  checkoutQris: (payload) => request('/api/billing/checkout-qris', { method: 'POST', body: payload }),
  qrisStatus: (orderId) => request(`/api/billing/qris-status/${orderId}`, { method: 'GET' }),
  payments: () => request('/api/billing/payments'),
}

export { getToken }
