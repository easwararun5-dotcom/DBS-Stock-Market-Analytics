import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend
} from 'recharts'
import api from '../api'
import { Loading, ErrorState, DataDateBadge, formatNumber, formatLargeNumber, PctBadge } from '../components/Common'

const RANGE_OPTIONS = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: '3Y', days: 1095 },
  { label: 'All', days: null },
]

export default function StockDetail() {
  const { ticker } = useParams()
  const navigate = useNavigate()
  const [detail, setDetail] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [chartLoading, setChartLoading] = useState(false)
  const [error, setError] = useState(null)
  const [range, setRange] = useState('1Y')
  const [chartType, setChartType] = useState('close')

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.companyDetail(ticker),
      loadHistory('1Y'),
    ])
      .then(([d]) => setDetail(d))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [ticker])

  const loadHistory = async (rangeLabel) => {
    setChartLoading(true)
    const opt = RANGE_OPTIONS.find(r => r.label === rangeLabel)
    const params = { limit: '50000', order: 'asc' }
    if (opt && opt.days) {
      const end = new Date('2026-01-30')
      const start = new Date(end)
      start.setDate(start.getDate() - opt.days)
      params.start_date = start.toISOString().split('T')[0]
      params.end_date = end.toISOString().split('T')[0]
    }
    try {
      const d = await api.priceHistory(ticker, params)
      setHistory(d.data || [])
    } catch (e) {
      console.error(e)
    }
    setChartLoading(false)
  }

  const handleRange = (label) => {
    setRange(label)
    loadHistory(label)
  }

  if (loading) return <Loading message={`Loading ${ticker}...`} />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />
  if (!detail) return null

  const { fundamentals: fund, summary: summ, latest_price: lp } = detail

  const chartData = history.map(h => ({
    date: h.trading_date,
    close: h.close_price,
    open: h.open_price,
    high: h.high_price,
    low: h.low_price,
    volume: h.volume,
    ma50: h.ma_50,
    ma200: h.ma_200,
  }))

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 24 }}>
        <div>
          <button className="btn btn-sm" onClick={() => navigate('/stocks')} style={{ marginBottom: 8 }}>
            ← Back to Explorer
          </button>
          <h2 style={{ fontSize: 28 }}>{detail.company_name}</h2>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 4 }}>
            <span className="badge badge-info" style={{ fontSize: 13 }}>{detail.ticker}</span>
            <span className="badge badge-info">{detail.sector_name}</span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {lp && (
            <>
              <div style={{ fontSize: 32, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                ₹{formatNumber(lp.close_price)}
              </div>
              <PctBadge value={lp.daily_return_pct} />
              <div style={{ marginTop: 4 }}><DataDateBadge date={lp.latest_trading_date} /></div>
            </>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      {lp && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
          <div className="stat-card">
            <div className="stat-label">Open</div>
            <div className="stat-value" style={{ fontSize: 20 }}>₹{formatNumber(lp.open_price)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">High</div>
            <div className="stat-value" style={{ fontSize: 20 }}>₹{formatNumber(lp.high_price)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Low</div>
            <div className="stat-value" style={{ fontSize: 20 }}>₹{formatNumber(lp.low_price)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Volume</div>
            <div className="stat-value" style={{ fontSize: 20 }}>{lp.volume ? Number(lp.volume).toLocaleString('en-IN') : '—'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">20d Volatility</div>
            <div className="stat-value" style={{ fontSize: 20 }}>{lp.volatility_20d_pct != null ? formatNumber(lp.volatility_20d_pct) + '%' : '—'}</div>
          </div>
        </div>
      )}

      {/* Price Chart */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h3>Price History</h3>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {RANGE_OPTIONS.map(r => (
              <button key={r.label} className={`btn btn-sm ${range === r.label ? 'btn-primary' : ''}`} onClick={() => handleRange(r.label)}>
                {r.label}
              </button>
            ))}
            <select className="input" value={chartType} onChange={e => setChartType(e.target.value)} style={{ padding: '4px 8px', fontSize: 12 }}>
              <option value="close">Close Price</option>
              <option value="ohlc">OHLC Range</option>
              <option value="volume">Volume</option>
            </select>
          </div>
        </div>
        <div className="card-body">
          {chartLoading ? (
            <Loading message="Loading chart..." />
          ) : chartData.length === 0 ? (
            <div className="empty-state"><p>No price data for selected range</p></div>
          ) : (
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer>
                {chartType === 'volume' ? (
                  <BarChartWrapper data={chartData} />
                ) : chartType === 'ohlc' ? (
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} minTickGap={40} />
                    <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                    <Tooltip labelFormatter={d => `Date: ${d}`} formatter={v => v != null ? `₹${Number(v).toFixed(2)}` : '—'} />
                    <Legend />
                    <Line type="monotone" dataKey="high" stroke="#0d904f" dot={false} strokeWidth={1} name="High" />
                    <Line type="monotone" dataKey="close" stroke="#1a73e8" dot={false} strokeWidth={2} name="Close" />
                    <Line type="monotone" dataKey="low" stroke="#d93025" dot={false} strokeWidth={1} name="Low" />
                  </LineChart>
                ) : (
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#1a73e8" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#1a73e8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} minTickGap={40} />
                    <YAxis tick={{ fontSize: 11 }} domain={['auto', 'auto']} />
                    <Tooltip labelFormatter={d => `Date: ${d}`} formatter={v => v != null ? `₹${Number(v).toFixed(2)}` : '—'} />
                    <Legend />
                    <Area type="monotone" dataKey="close" stroke="#1a73e8" fill="url(#colorClose)" strokeWidth={2} dot={false} name="Close Price" />
                    {chartData[0]?.ma50 != null && (
                      <Line type="monotone" dataKey="ma50" stroke="#f9ab00" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="MA 50" />
                    )}
                    {chartData[0]?.ma200 != null && (
                      <Line type="monotone" dataKey="ma200" stroke="#9334e6" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="MA 200" />
                    )}
                  </AreaChart>
                )}
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Fundamentals & Summary */}
      <div className="grid-2">
        {/* Fundamentals */}
        <div className="card">
          <div className="card-header"><h3>Fundamentals</h3></div>
          <div className="card-body">
            {fund ? (
              <table style={{ width: '100%' }}>
                <tbody>
                  {[
                    ['Market Cap', fund.market_cap ? `₹${formatLargeNumber(fund.market_cap)}` : '—'],
                    ['P/E Ratio', formatNumber(fund.pe_ratio)],
                    ['Forward P/E', formatNumber(fund.forward_pe)],
                    ['Price to Book', formatNumber(fund.price_to_book)],
                    ['EPS', fund.eps != null ? `₹${formatNumber(fund.eps)}` : '—'],
                    ['Dividend Yield', fund.dividend_yield != null ? formatNumber(fund.dividend_yield) + '%' : '—'],
                    ['Beta', formatNumber(fund.beta)],
                    ['Valuation Tier', fund.valuation_tier || '—'],
                    ['Dividend Tier', fund.dividend_tier || '—'],
                  ].map(([label, val]) => (
                    <tr key={label}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)', fontSize: 13 }}>{label}</td>
                      <td className="text-right text-mono" style={{ padding: '8px 0', fontWeight: 500 }}>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No fundamentals data available</p>
            )}
          </div>
        </div>

        {/* Summary Statistics */}
        <div className="card">
          <div className="card-header"><h3>Historical Summary</h3></div>
          <div className="card-body">
            {summ ? (
              <table style={{ width: '100%' }}>
                <tbody>
                  {[
                    ['Trading Days', formatNumber(summ.total_trading_days, 0)],
                    ['First Trade', summ.first_trading_date || '—'],
                    ['Last Trade', summ.last_trading_date || '—'],
                    ['Starting Price', `₹${formatNumber(summ.starting_price)}`],
                    ['Ending Price', `₹${formatNumber(summ.ending_price)}`],
                    ['Total Return', summ.total_return_pct != null ? `${formatNumber(summ.total_return_pct)}%` : '—'],
                    ['All-time High', `₹${formatNumber(summ.highest_price)}`],
                    ['All-time Low', `₹${formatNumber(summ.lowest_price)}`],
                    ['Avg Daily Volume', formatLargeNumber(summ.avg_daily_volume)],
                    ['Volatility', summ.volatility_pct != null ? formatNumber(summ.volatility_pct) + '%' : '—'],
                    ['Total Dividends', `₹${formatNumber(summ.total_dividends_paid)}`],
                    ['Splits', summ.number_of_splits],
                  ].map(([label, val]) => (
                    <tr key={label}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)', fontSize: 13 }}>{label}</td>
                      <td className="text-right text-mono" style={{ padding: '8px 0', fontWeight: 500 }}>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No summary data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Volume bar chart helper
import { BarChart, Bar } from 'recharts'

function BarChartWrapper({ data }) {
  return (
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
      <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} minTickGap={40} />
      <YAxis tick={{ fontSize: 11 }} />
      <Tooltip labelFormatter={d => `Date: ${d}`} formatter={v => v != null ? Number(v).toLocaleString('en-IN') : '—'} />
      <Bar dataKey="volume" fill="#1a73e8" opacity={0.7} name="Volume" />
    </BarChart>
  )
}
