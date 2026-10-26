import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { Loading, ErrorState, EmptyState, DataDateBadge, formatNumber, PctBadge } from '../components/Common'

export default function StockExplorer() {
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [sortKey, setSortKey] = useState('ticker')
  const [sortDir, setSortDir] = useState('asc')
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    api.latestPrices()
      .then(d => setPrices(d.data || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Loading stock data..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const sectors = [...new Set(prices.map(p => p.sector_name))].sort()

  let filtered = prices.filter(p => {
    const q = search.toLowerCase()
    const matchSearch = !q || p.ticker.toLowerCase().includes(q) || p.company_name.toLowerCase().includes(q)
    const matchSector = !sectorFilter || p.sector_name === sectorFilter
    return matchSearch && matchSector
  })

  filtered.sort((a, b) => {
    let va = a[sortKey], vb = b[sortKey]
    if (typeof va === 'string') va = va.toLowerCase()
    if (typeof vb === 'string') vb = vb.toLowerCase()
    if (va == null) return 1
    if (vb == null) return -1
    if (va < vb) return sortDir === 'asc' ? -1 : 1
    if (va > vb) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sortIcon = (key) => {
    if (sortKey !== key) return ''
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  const latestDate = prices.length > 0 ? prices[0].latest_trading_date : null

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2>Stock Explorer</h2>
          <p>Browse and search all {prices.length} companies</p>
        </div>
        <DataDateBadge date={latestDate} />
      </div>

      {/* Filters */}
      <div className="input-group" style={{ marginBottom: 20 }}>
        <input
          className="input"
          type="text"
          placeholder="Search ticker or company..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ minWidth: 250 }}
        />
        <select className="input" value={sectorFilter} onChange={e => setSectorFilter(e.target.value)}>
          <option value="">All Sectors</option>
          {sectors.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Showing {filtered.length} of {prices.length}
        </span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState message="No stocks match your search" icon="🔍" />
      ) : (
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th onClick={() => handleSort('ticker')} style={{cursor:'pointer'}}>Ticker{sortIcon('ticker')}</th>
                    <th onClick={() => handleSort('company_name')} style={{cursor:'pointer'}}>Company{sortIcon('company_name')}</th>
                    <th>Sector</th>
                    <th className="text-right" onClick={() => handleSort('close_price')} style={{cursor:'pointer'}}>Close{sortIcon('close_price')}</th>
                    <th className="text-right" onClick={() => handleSort('daily_return_pct')} style={{cursor:'pointer'}}>Day Chg%{sortIcon('daily_return_pct')}</th>
                    <th className="text-right" onClick={() => handleSort('volume')} style={{cursor:'pointer'}}>Volume{sortIcon('volume')}</th>
                    <th className="text-right">High</th>
                    <th className="text-right">Low</th>
                    <th className="text-right" onClick={() => handleSort('volatility_20d_pct')} style={{cursor:'pointer'}}>Vol 20d%{sortIcon('volatility_20d_pct')}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(s => (
                    <tr key={s.ticker} onClick={() => navigate(`/stocks/${s.ticker}`)} style={{ cursor: 'pointer' }}>
                      <td className="ticker-link">{s.ticker}</td>
                      <td>{s.company_name}</td>
                      <td><span className="badge badge-info">{s.sector_name}</span></td>
                      <td className="text-right text-mono">₹{formatNumber(s.close_price)}</td>
                      <td className="text-right"><PctBadge value={s.daily_return_pct} /></td>
                      <td className="text-right text-mono">{s.volume ? Number(s.volume).toLocaleString('en-IN') : '—'}</td>
                      <td className="text-right text-mono">₹{formatNumber(s.high_price)}</td>
                      <td className="text-right text-mono">₹{formatNumber(s.low_price)}</td>
                      <td className="text-right text-mono">{s.volatility_20d_pct != null ? formatNumber(s.volatility_20d_pct) + '%' : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
