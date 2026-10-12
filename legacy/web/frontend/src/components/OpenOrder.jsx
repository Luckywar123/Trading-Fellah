import React, { useState } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function OpenOrder() {
  const [formData, setFormData] = useState({
    symbol: 'EUR/USD',
    direction: 'LONG',
    size: 0.1,
    stop_loss: '',
    take_profit: '',
    trailing_mode: 'FIXED_10PIPS'
  })
  
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      const res = await axios.post(`${API_BASE}/api/trades/open`, formData)
      setResponse({ success: true, data: res.data })
      alert('Order opened successfully!')
    } catch (err) {
      setResponse({ success: false, error: err.message })
      alert('Order failed: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleEmergencyClose = async () => {
    if (!confirm('ARE YOU SURE? This will close ALL positions immediately!')) return
    
    try {
      await axios.post(`${API_BASE}/api/system/emergency-close`)
      alert('All positions closed!')
    } catch (err) {
      alert('Failed to close positions: ' + err.message)
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <span>🎯 Open Manual Order</span>
        <button className="btn btn-danger" onClick={handleEmergencyClose}>
          🚨 EMERGENCY CLOSE ALL
        </button>
      </div>
      
      <form onSubmit={handleSubmit} style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Symbol</label>
          <select
            value={formData.symbol}
            onChange={(e) => setFormData({...formData, symbol: e.target.value})}
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              background: 'var(--bg)', border: '1px solid #444', color: 'white'
            }}
          >
            <option value="EUR/USD">EUR/USD</option>
            <option value="GBP/USD">GBP/USD</option>
            <option value="BTC/USDT">BTC/USDT</option>
            <option value="ETH/USDT">ETH/USDT</option>
          </select>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Direction</label>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              onClick={() => setFormData({...formData, direction: 'LONG'})}
              className={`btn ${formData.direction === 'LONG' ? 'btn-success' : ''}`}
              style={{ flex: 1, opacity: formData.direction !== 'LONG' ? 0.5 : 1 }}
            >
              BUY 🟢
            </button>
            <button
              type="button"
              onClick={() => setFormData({...formData, direction: 'SHORT'})}
              className={`btn btn-danger ${formData.direction === 'SHORT' ? '' : ''}`}
              style={{ flex: 1, opacity: formData.direction !== 'SHORT' ? 0.5 : 1 }}
            >
              SELL 🔴
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Size (Lots)</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={formData.size}
            onChange={(e) => setFormData({...formData, size: parseFloat(e.target.value)})}
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              background: 'var(--bg)', border: '1px solid #444', color: 'white'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Stop Loss (Price)</label>
          <input
            type="number"
            step="0.00001"
            value={formData.stop_loss}
            onChange={(e) => setFormData({...formData, stop_loss: parseFloat(e.target.value)})}
            placeholder="Auto-calculated if empty"
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              background: 'var(--bg)', border: '1px solid #444', color: 'white'
            }}
          />
        </div>

        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Take Profit (Price)</label>
          <input
            type="number"
            step="0.00001"
            value={formData.take_profit}
            onChange={(e) => setFormData({...formData, take_profit: parseFloat(e.target.value)})}
            placeholder="Auto-calculated if empty"
            style={{
              width: '100%', padding: '10px', borderRadius: '6px',
              background: 'var(--bg)', border: '1px solid #444', color: 'white'
            }}
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
          style={{ width: '100%', padding: '15px', fontSize: '16px' }}
        >
          {loading ? 'Opening...' : 'OPEN ORDER'}
        </button>
      </form>

      {response && (
        <div style={{ 
          marginTop: '20px', padding: '15px', borderRadius: '6px',
          background: response.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          color: response.success ? 'var(--success)' : 'var(--danger)'
        }}>
          {response.success ? '✅ Order placed successfully!' : `❌ Error: ${response.error}`}
        </div>
      )}
    </div>
  )
}