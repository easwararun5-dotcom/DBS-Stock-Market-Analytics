import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { Loading, ErrorState, EmptyState, DemoBanner, formatNumber, PctBadge } from '../components/Common'

export default function Watchlist() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  // Demo user ID = 1
  const userId = 1

  useEffect(() => {
    api.watchlist(userId)
      .then(d => setItems(d.data || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Loading watchlist..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  return (
    <div>
      <div className="page-header">
        <h2>Watchlist</h2>
        <p>Track stocks you're interested in</p>
      </div>

      <DemoBanner />

      {items.length === 0 ? (
        <EmptyState
          icon="⭐"
          message="Your watchlist is empty. Watchlist features require user accounts to be set up. Browse the Stock Explorer to discover stocks."
        />
      ) : (
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Company</th>
                    <th>Sector</th>
                    <th className="text-right">Latest Price</th>
                    <th className="text-right">Day Change%</th>
                    <th className="text-right">Alert Price</th>
                    <th>Added</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(w => (
                    <tr key={w.watchlist_id} onClick={() => navigate(`/stocks/${w.ticker}`)} style={{ cursor: 'pointer' }}>
                      <td className="ticker-link">{w.ticker}</td>
                      <td>{w.company_name}</td>
                      <td><span className="badge badge-info">{w.sector_name}</span></td>
                      <td className="text-right text-mono">{w.latest_price ? `₹${formatNumber(w.latest_price)}` : '—'}</td>
                      <td className="text-right"><PctBadge value={w.daily_return_pct} /></td>
                      <td className="text-right text-mono">{w.alert_price ? `₹${formatNumber(w.alert_price)}` : '—'}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{w.added_at ? new Date(w.added_at).toLocaleDateString() : '—'}</td>
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
