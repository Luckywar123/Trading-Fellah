import React, { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function Dashboard() {
  const [data, setData] = useState(null)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/dashboard/overview`)
      setData(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  if (!data) return <div className="container"><div>Loading...</div></div>

  return (
    <div className="container">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--primary)' }}>
            ${data.equity.toFixed(2)}
          </div>
          <div>Current Equity</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--primary)' }}>
            {data.win_rate?.toFixed(1) || 0}%
          </div>
          <div>Win Rate</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: 'var(--primary)' }}>
            {data.active_positions?.length || 0}
          </div>
          <div>Active Positions</div>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: data.daily_pnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {data.daily_pnl >= 0 ? '+' : ''}{data.daily_pnl?.toFixed(2) || 0}
          </div>
          <div>Daily PnL</div>
        </div>
      </div>

      <div className="card">
        <h3>Active Positions</h3>
        {data.active_positions && data.active_positions.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #444' }}>Symbol</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #444' }}>Direction</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #444' }}>Entry</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #444' }}>SL</th>
                <th style={{ textAlign: 'left', padding: '10px', borderBottom: '1px solid #444' }}>Trail</th>
              </tr>
            </thead>
            <tbody>
              {data.active_positions.map((pos, i) => (
                <tr key={i}>
                  <td style={{ padding: '10px', borderBottom: '1px solid #333' }}>{pos.symbol}</td>
                  <td style={{ padding: '10px' }}>
                    <span className="badge" style={{ background: pos.direction === 'LONG' ? 'var(--success)' : 'var(--danger)', color: 'white' }}>
                      {pos.direction}
                    </span>
                  </td>
                  <td style={{ padding: '10px' }}>{pos.entry_price?.toFixed(5)}</td>
                  <td style={{ padding: '10px' }}>{pos.stop_loss?.toFixed(5)}</td>
                  <td style={{ padding: '10px' }}>
                    {pos.trailing_active ? (
                      <span className="badge" style={{ background: '#f59e0b' }}>Active</span>
                    ) : (
                      <span className="badge" style={{ background: '#666' }}>Wait</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div>No active positions</div>
        )}
      </div>
    </div>
  )
}
