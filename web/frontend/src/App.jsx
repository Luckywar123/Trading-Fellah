import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import OpenOrder from './components/OpenOrder'
import History from './components/History'

function App() {
  return (
    <div>
      <nav style={{ padding: '20px', background: 'var(--bg-card)', marginBottom: '20px' }}>
        <div className="container" style={{ display: 'flex', alignItems: 'center' }}>
          <h1 style={{ marginRight: '40px' }}>🎯 Sniper Bot v3.0</h1>
          <Link to="/" style={{ marginRight: '20px', color: 'white', textDecoration: 'none' }}>Dashboard</Link>
          <Link to="/open-order" style={{ marginRight: '20px', color: 'white', textDecoration: 'none' }}>Open Order</Link>
          <Link to="/history" style={{ color: 'white', textDecoration: 'none' }}>History</Link>
        </div>
      </nav>
      
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/open-order" element={<OpenOrder />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </div>
  )
}

export default App