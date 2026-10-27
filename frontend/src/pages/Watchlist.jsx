import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { Loading, ErrorState, EmptyState, formatNumber, PctBadge } from '../components/Common';

export default function Watchlist() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Add stock bar states
  const [selectedTicker, setSelectedTicker] = useState('TCS.NS');
  const [alertPrice, setAlertPrice] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState(null);

  const loadWatchlistAndCompanies = async () => {
    try {
      setLoading(true);
      setError(null);
      const [watchlistRes, companiesRes] = await Promise.all([
        api.getWatchlist(),
        api.companies({ limit: 100 }),
      ]);
      setItems(watchlistRes.data || []);
      const compList = companiesRes.data || [];
      setCompanies(compList);
      if (compList.length > 0) {
        setSelectedTicker(compList[0].ticker);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWatchlistAndCompanies();
  }, [isAuthenticated]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setAddError(null);
    if (!selectedTicker) return;

    setAdding(true);
    try {
      await api.addWatchlist({
        ticker: selectedTicker,
        alert_price: alertPrice ? parseFloat(alertPrice) : null,
      });
      setAlertPrice('');
      // Refresh items
      const res = await api.getWatchlist();
      setItems(res.data || []);
    } catch (err) {
      setAddError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (e, ticker) => {
    e.stopPropagation();
    try {
      await api.removeWatchlist(ticker);
      setItems((prev) => prev.filter((item) => item.ticker !== ticker));
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isAuthenticated) {
    return (
      <div>
        <div className="page-header">
          <h2>Stock Watchlist</h2>
          <p>Monitor your favorite stocks, real-time prices & target price alerts</p>
        </div>
        <div className="empty-state" style={{ maxWidth: 600, margin: '40px auto' }}>
          <div className="empty-icon">⭐</div>
          <h3 style={{ color: '#fff', marginBottom: 8 }}>Authentication Required</h3>
          <p className="empty-message">
            Sign in or register to maintain your personal watchlist saved directly in PostgreSQL, track price targets, and view live market changes.
          </p>
          <div className="empty-action" style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Link to="/login" className="btn btn-primary btn-lg">
              Sign In to Your Watchlist
            </Link>
            <Link to="/register" className="btn btn-secondary btn-lg">
              Create New Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) return <Loading message="Loading your watchlist..." />;
  if (error) return <ErrorState message={error} onRetry={loadWatchlistAndCompanies} />;

  const isAlreadyWatchlisted = items.some((i) => i.ticker === selectedTicker);

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h2>Stock Watchlist</h2>
          <p>Personalized market monitoring and target price alerts</p>
        </div>
      </div>

      {/* Add Stock to Watchlist Card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h3>➕ Track New Stock</h3>
        </div>
        <div className="card-body">
          {addError && (
            <div className="auth-alert error" style={{ marginBottom: 16 }}>
              <span>⚠️ {addError}</span>
            </div>
          )}
          <form onSubmit={handleAdd} style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: '1 1 260px' }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                SELECT COMPANY
              </label>
              <select
                className="form-input"
                value={selectedTicker}
                onChange={(e) => setSelectedTicker(e.target.value)}
              >
                {companies.map((c) => (
                  <option key={c.ticker} value={c.ticker}>
                    {c.ticker} — {c.company_name} ({c.latest_price ? `₹${formatNumber(c.latest_price)}` : 'N/A'})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ flex: '0 1 180px' }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                ALERT PRICE (₹ OPTIONAL)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                className="form-input"
                placeholder="Target price..."
                value={alertPrice}
                onChange={(e) => setAlertPrice(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={adding || isAlreadyWatchlisted}
              style={{ height: 42 }}
            >
              {adding ? 'Adding...' : isAlreadyWatchlisted ? 'Already in Watchlist' : '+ Add to Watchlist'}
            </button>
          </form>
        </div>
      </div>

      {/* Watchlist Table */}
      {items.length === 0 ? (
        <EmptyState
          icon="⭐"
          message="Your watchlist is currently empty. Select a stock above and click '+ Add to Watchlist' to start monitoring."
        />
      ) : (
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Company Name</th>
                    <th>Sector</th>
                    <th className="text-right">Latest Price</th>
                    <th className="text-right">Day Return</th>
                    <th className="text-right">Alert Price</th>
                    <th>Date Added</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((w) => (
                    <tr
                      key={w.watchlist_id || w.ticker}
                      onClick={() => navigate(`/stocks/${w.ticker}`)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className="ticker-link">{w.ticker}</td>
                      <td style={{ fontWeight: 500 }}>{w.company_name}</td>
                      <td>
                        <span className="badge-info">{w.sector_name || 'Market'}</span>
                      </td>
                      <td className="text-right text-mono" style={{ fontWeight: 600 }}>
                        {w.latest_price ? `₹${formatNumber(w.latest_price)}` : '—'}
                      </td>
                      <td className="text-right">
                        <PctBadge value={w.daily_return_pct} />
                      </td>
                      <td className="text-right text-mono">
                        {w.alert_price ? (
                          <span style={{ color: '#f59e0b', fontWeight: 600 }}>
                            ₹{formatNumber(w.alert_price)}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {w.added_at ? new Date(w.added_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="text-right">
                        <button
                          className="btn-icon"
                          onClick={(e) => handleRemove(e, w.ticker)}
                          title="Remove from Watchlist"
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
