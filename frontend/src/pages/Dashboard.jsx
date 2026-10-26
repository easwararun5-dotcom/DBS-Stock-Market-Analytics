import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import api from '../api'
import { Loading, ErrorState, DataDateBadge, formatNumber, formatLargeNumber, PctBadge } from '../components/Common'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    setError(null)
    api.dashboard()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  if (loading) return <Loading message="Loading dashboard..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data) return null

  const sectorChart = (data.sector_breakdown || []).map(s => ({
    name: s.sector_name,
    value: s.total_market_cap_trillion_inr || 0,
  }))

  const COLORS = [
    '#1a73e8','#0d904f','#d93025','#f9ab00','#9334e6',
    '#e8710a','#1e8e3e','#185abc','#c5221f','#ea8600',
    '#a142f4','#129eaf','#e37400',
  ]

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Dashboard</h2>
          <p>Market overview and key statistics</p>
        </div>
        <DataDateBadge date={data.latest_data_date} />
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Companies</div>
          <div className="stat-value">{data.total_companies}</div>
          <div className="stat-sub">Nifty 50 universe</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sectors</div>
          <div className="stat-value">{data.total_sectors}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Price Records</div>
          <div className="stat-value">{formatNumber(data.total_price_records, 0)}</div>
          <div className="stat-sub">Daily OHLCV data</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Market Cap</div>
          <div className="stat-value">₹{data.market_cap_total_trillion}T</div>
          <div className="stat-sub">Combined market capitalisation</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Corporate Actions</div>
          <div className="stat-value">{formatNumber(data.total_corporate_actions, 0)}</div>
          <div className="stat-sub">Dividends & splits</div>
        </div>
      </div>

      {/* Gainers / Losers + Sector Chart */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Top Gainers */}
        <div className="card">
          <div className="card-header"><h3>🟢 Top Gainers (Latest Day)</h3></div>
          <div className="card-body" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Change</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_gainers || []).map(s => (
                  <tr key={s.ticker} style={{ cursor: 'pointer' }} onClick={() => navigate(`/stocks/${s.ticker}`)}>
                    <td className="ticker-link">{s.ticker}</td>
                    <td>{s.company_name}</td>
                    <td className="text-right text-mono">₹{formatNumber(s.close_price)}</td>
                    <td className="text-right"><PctBadge value={s.daily_return_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Losers */}
        <div className="card">
          <div className="card-header"><h3>🔴 Top Losers (Latest Day)</h3></div>
          <div className="card-body" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Change</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_losers || []).map(s => (
                  <tr key={s.ticker} style={{ cursor: 'pointer' }} onClick={() => navigate(`/stocks/${s.ticker}`)}>
                    <td className="ticker-link">{s.ticker}</td>
                    <td>{s.company_name}</td>
                    <td className="text-right text-mono">₹{formatNumber(s.close_price)}</td>
                    <td className="text-right"><PctBadge value={s.daily_return_pct} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Sector Breakdown Chart */}
      <div className="card">
        <div className="card-header"><h3>Sector Market Cap Distribution (₹ Trillion)</h3></div>
        <div className="card-body">
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer>
              <BarChart data={sectorChart} layout="vertical" margin={{ left: 120, right: 20, top: 5, bottom: 5 }}>
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={110} />
                <Tooltip formatter={(v) => [`₹${v.toFixed(2)}T`, 'Market Cap']} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {sectorChart.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Sector Table */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header"><h3>Sector Performance Overview</h3></div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Sector</th>
                  <th className="text-center">Companies</th>
                  <th className="text-right">Market Cap (₹T)</th>
                  <th className="text-right">Avg P/E</th>
                </tr>
              </thead>
              <tbody>
                {(data.sector_breakdown || []).map(s => (
                  <tr key={s.sector_name}>
                    <td><strong>{s.sector_name}</strong></td>
                    <td className="text-center">{s.num_companies}</td>
                    <td className="text-right text-mono">{formatNumber(s.total_market_cap_trillion_inr)}</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_pe_ratio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
