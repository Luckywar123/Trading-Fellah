import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import { AccountProvider } from './context/AccountContext.jsx'
import Layout from './components/Layout.jsx'

import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Trade from './pages/Trade.jsx'
import RiskSettings from './pages/RiskSettings.jsx'
import Backtest from './pages/Backtest.jsx'
import Automation from './pages/Automation.jsx'
import AIInsights from './pages/AIInsights.jsx'
import Billing from './pages/Billing.jsx'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-void text-ink-muted font-mono text-sm">
        Memuat sesi…
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return (
    <AccountProvider>
      <Layout>{children}</Layout>
    </AccountProvider>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/trade" element={<Protected><Trade /></Protected>} />
      <Route path="/risk" element={<Protected><RiskSettings /></Protected>} />
      <Route path="/backtest" element={<Protected><Backtest /></Protected>} />
      <Route path="/automation" element={<Protected><Automation /></Protected>} />
      <Route path="/ai" element={<Protected><AIInsights /></Protected>} />
      <Route path="/billing" element={<Protected><Billing /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
