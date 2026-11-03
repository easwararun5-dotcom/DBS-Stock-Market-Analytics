import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, Legend } from 'recharts'
import api from '../api'
import { Loading, ErrorState, formatNumber, formatLargeNumber, PctBadge } from '../components/Common'

const COLORS = [
  '#1a73e8','#0d904f','#d93025','#f9ab00','#9334e6',
  '#e8710a','#1e8e3e','#185abc','#c5221f','#ea8600',
  '#a142f4','#129eaf','#e37400',
]

export default function Sectors() {
  const [sectors, setSectors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.sectors()
      .then(d => setSectors(d.data || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Loading sector data..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const chartData = sectors.map(s => ({
    name: s.sector_name,
    pe: s.avg_pe_ratio,
    return: s.avg_total_return_pct,
  }))

  return (
    <div>
      <div className="page-header">
        <h2>Sector Analysis</h2>
        <p>Sector-level performance and valuation metrics across {sectors.length} sectors</p>
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header"><h3>Average P/E Ratio by Sector</h3></div>
          <div className="card-body">
            <div style={{ width: '100%', height: 350 }}>
              <ResponsiveContainer>
                <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 20, top: 5, bottom: 5 }}>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip formatter={v => v != null ? v.toFixed(2) : '—'} />
                  <Bar dataKey="pe" name="Avg P/E" radius={[0, 4, 4, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><h3>Average Total Return % by Sector</h3></div>
          <div className="card-body">
            <div style={{ width: '100%', height: 350 }}>
              <ResponsiveContainer>
                <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 20, top: 5, bottom: 5 }}>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip formatter={v => v != null ? v.toFixed(2) + '%' : '—'} />
                  <Bar dataKey="return" name="Avg Return %" radius={[0, 4, 4, 0]}>
                    {chartData.map((e, i) => (
                      <Cell key={i} fill={e.return >= 0 ? '#0d904f' : '#d93025'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        <div className="card-header"><h3>Detailed Sector Metrics</h3></div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Sector</th>
                  <th className="text-center">Companies</th>
                  <th className="text-right">Market Cap (₹T)</th>
                  <th className="text-right">Avg P/E</th>
                  <th className="text-right">Avg Fwd P/E</th>
                  <th className="text-right">Avg P/B</th>
                  <th className="text-right">Avg Div Yield</th>
                  <th className="text-right">Avg Beta</th>
                  <th className="text-right">Avg Return%</th>
                  <th className="text-right">Avg Volatility%</th>
                </tr>
              </thead>
              <tbody>
                {sectors.map(s => (
                  <tr key={s.sector_id}>
                    <td><strong>{s.sector_name}</strong></td>
                    <td className="text-center">{s.num_companies}</td>
                    <td className="text-right text-mono">{formatNumber(s.total_market_cap_trillion_inr)}</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_pe_ratio)}</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_forward_pe)}</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_price_to_book)}</td>
                    <td className="text-right text-mono">{s.avg_dividend_yield != null ? formatNumber(s.avg_dividend_yield, 4) : '—'}</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_beta, 4)}</td>
                    <td className="text-right"><PctBadge value={s.avg_total_return_pct} /></td>
                    <td className="text-right text-mono">{s.avg_volatility_pct != null ? formatNumber(s.avg_volatility_pct, 4) + '%' : '—'}</td>
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
