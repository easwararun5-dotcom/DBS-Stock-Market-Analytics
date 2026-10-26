import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import api from '../api'
import { Loading, ErrorState, EmptyState, DemoBanner, formatNumber, PctBadge } from '../components/Common'

const COLORS = ['#1a73e8','#0d904f','#d93025','#f9ab00','#9334e6','#e8710a','#1e8e3e','#185abc','#c5221f','#ea8600']

export default function Portfolio() {
  const [holdings, setHoldings] = useState([])
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('holdings')
  const navigate = useNavigate()

  // Demo user ID = 1
  const userId = 1

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.portfolioHoldings(userId),
      api.portfolioTransactions(userId),
    ])
      .then(([h, t]) => {
        setHoldings(h.data || [])
        setTransactions(t.data || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Loading portfolio..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const totalInvested = holdings.reduce((s, h) => s + (h.invested_value || 0), 0)
  const totalCurrent = holdings.reduce((s, h) => s + (h.current_value || 0), 0)
  const totalPL = totalCurrent - totalInvested
  const totalPLPct = totalInvested > 0 ? ((totalPL / totalInvested) * 100) : 0

  const pieData = holdings.map(h => ({
    name: h.ticker,
    value: h.current_value || h.invested_value || 0,
  }))

  return (
    <div>
      <div className="page-header">
        <h2>Portfolio</h2>
        <p>Track your investment holdings and performance</p>
      </div>

      <DemoBanner />

      {holdings.length === 0 ? (
        <EmptyState
          icon="💼"
          message="No portfolio holdings found. Portfolio features require user accounts and transactions to be set up."
        />
      ) : (
        <>
          {/* Summary Stats */}
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
            <div className="stat-card">
              <div className="stat-label">Holdings</div>
              <div className="stat-value">{holdings.length}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Invested Value</div>
              <div className="stat-value">₹{formatNumber(totalInvested)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Current Value</div>
              <div className="stat-value">₹{formatNumber(totalCurrent)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Total P&L</div>
              <div className="stat-value">
                <span className={totalPL >= 0 ? 'positive' : 'negative'}>
                  ₹{formatNumber(totalPL)} ({totalPLPct.toFixed(2)}%)
                </span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <button className={`btn ${tab === 'holdings' ? 'btn-primary' : ''}`} onClick={() => setTab('holdings')}>
              Holdings
            </button>
            <button className={`btn ${tab === 'allocation' ? 'btn-primary' : ''}`} onClick={() => setTab('allocation')}>
              Allocation
            </button>
            <button className={`btn ${tab === 'transactions' ? 'btn-primary' : ''}`} onClick={() => setTab('transactions')}>
              Transactions
            </button>
          </div>

          {tab === 'holdings' && (
            <div className="card">
              <div className="card-body" style={{ padding: 0 }}>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Ticker</th>
                        <th>Company</th>
                        <th>Sector</th>
                        <th className="text-right">Qty</th>
                        <th className="text-right">Avg Buy</th>
                        <th className="text-right">Current</th>
                        <th className="text-right">Invested</th>
                        <th className="text-right">Current Val</th>
                        <th className="text-right">P&L</th>
                        <th className="text-right">P&L %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.map(h => (
                        <tr key={h.holding_id} onClick={() => navigate(`/stocks/${h.ticker}`)} style={{ cursor: 'pointer' }}>
                          <td className="ticker-link">{h.ticker}</td>
                          <td>{h.company_name}</td>
                          <td><span className="badge badge-info">{h.sector_name}</span></td>
                          <td className="text-right text-mono">{formatNumber(h.quantity, 0)}</td>
                          <td className="text-right text-mono">₹{formatNumber(h.average_buy_price)}</td>
                          <td className="text-right text-mono">₹{formatNumber(h.current_price)}</td>
                          <td className="text-right text-mono">₹{formatNumber(h.invested_value)}</td>
                          <td className="text-right text-mono">₹{formatNumber(h.current_value)}</td>
                          <td className="text-right">
                            <span className={h.profit_loss >= 0 ? 'positive' : 'negative'}>
                              ₹{formatNumber(h.profit_loss)}
                            </span>
                          </td>
                          <td className="text-right"><PctBadge value={h.profit_loss_pct} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {tab === 'allocation' && (
            <div className="card">
              <div className="card-header"><h3>Portfolio Allocation</h3></div>
              <div className="card-body">
                {pieData.length > 0 ? (
                  <div style={{ width: '100%', height: 400 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" outerRadius={150} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}>
                          {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip formatter={v => `₹${formatNumber(v)}`} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyState message="No allocation data" />
                )}
              </div>
            </div>
          )}

          {tab === 'transactions' && (
            <div className="card">
              <div className="card-body" style={{ padding: 0 }}>
                {transactions.length === 0 ? (
                  <EmptyState message="No transactions recorded" icon="📋" />
                ) : (
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Ticker</th>
                          <th>Company</th>
                          <th>Type</th>
                          <th className="text-right">Qty</th>
                          <th className="text-right">Price</th>
                          <th className="text-right">Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {transactions.map(t => (
                          <tr key={t.transaction_id}>
                            <td>{t.transaction_date}</td>
                            <td className="ticker-link" onClick={() => navigate(`/stocks/${t.ticker}`)}>{t.ticker}</td>
                            <td>{t.company_name}</td>
                            <td>
                              <span className={`badge ${t.transaction_type === 'BUY' ? 'badge-success' : t.transaction_type === 'SELL' ? 'badge-danger' : 'badge-info'}`}>
                                {t.transaction_type}
                              </span>
                            </td>
                            <td className="text-right text-mono">{formatNumber(t.quantity, 0)}</td>
                            <td className="text-right text-mono">₹{formatNumber(t.price)}</td>
                            <td className="text-right text-mono">₹{formatNumber(t.quantity * t.price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
