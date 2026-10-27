import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { Loading, ErrorState, DataDateBadge, formatNumber, formatLargeNumber, PctBadge } from '../components/Common';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const load = (preferredPid = null) => {
    setLoading(true);
    setError(null);
    const savedPid = preferredPid || localStorage.getItem('dbs_active_portfolio_id');
    const params = savedPid ? { portfolio_id: savedPid } : {};
    api.dashboard(params)
      .then((res) => {
        setData(res);
        if (res?.user_portfolio?.portfolio_id) {
          localStorage.setItem('dbs_active_portfolio_id', res.user_portfolio.portfolio_id);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const savedPid = localStorage.getItem('dbs_active_portfolio_id');
    load(savedPid);
  }, [isAuthenticated]);

  const handlePortfolioChange = (e) => {
    const newPid = parseInt(e.target.value);
    if (newPid) {
      localStorage.setItem('dbs_active_portfolio_id', newPid);
      load(newPid);
    }
  };

  if (loading) return <Loading message="Loading financial dashboard..." />;
  if (error) return <ErrorState message={error} onRetry={() => load()} />;
  if (!data) return null;

  const sectorChart = (data.sector_breakdown || []).map((s) => ({
    name: s.sector_name,
    value: s.total_market_cap_trillion_inr || 0,
  }));

  const COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
    '#06b6d4', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
    '#e11d48', '#0284c7', '#d97706',
  ];

  const userPortfolio = data.user_portfolio;
  const portfolioTotalValue = userPortfolio
    ? (userPortfolio.total_value ?? userPortfolio.total_portfolio_value ?? ((parseFloat(userPortfolio.cash_balance) || 0) + (parseFloat(userPortfolio.market_value) || 0)))
    : 0;
  const portfolioPL = userPortfolio
    ? (userPortfolio.total_pl ?? userPortfolio.unrealized_profit_loss ?? userPortfolio.profit_loss ?? 0)
    : 0;
  const portfolioHoldingsCount = userPortfolio
    ? (userPortfolio.total_holdings ?? userPortfolio.active_holdings_count ?? 0)
    : 0;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2>Market Dashboard</h2>
          <p>Real-time analytics, market depth & portfolio performance</p>
        </div>
        <DataDateBadge date={data.latest_data_date} />
      </div>

      {/* Authenticated User Portfolio Banner */}
      {isAuthenticated && userPortfolio ? (
        <div className="card" style={{ background: 'linear-gradient(135deg, #111827 0%, #1e293b 100%)', borderColor: '#3b82f6', marginBottom: 24 }}>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  ⭐ ACTIVE PORTFOLIO:
                </span>
                {data.user_portfolios && data.user_portfolios.length > 1 ? (
                  <select
                    className="form-input"
                    style={{
                      width: 'auto',
                      padding: '2px 8px',
                      fontSize: 12,
                      fontWeight: 700,
                      color: '#38bdf8',
                      background: '#0f172a',
                      borderColor: '#3b82f6',
                      borderRadius: 4,
                      cursor: 'pointer'
                    }}
                    value={userPortfolio.portfolio_id}
                    onChange={handlePortfolioChange}
                  >
                    {data.user_portfolios.map((p) => (
                      <option key={p.portfolio_id} value={p.portfolio_id}>
                        {p.portfolio_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#ffffff', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                    {userPortfolio.portfolio_name}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#ffffff', marginTop: 4 }}>
                ₹{formatNumber(portfolioTotalValue)}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                Cash: ₹{formatNumber(userPortfolio.cash_balance)} &middot; {portfolioHoldingsCount} Active Holdings &middot;{' '}
                <span className={portfolioPL >= 0 ? 'positive' : 'negative'}>
                  {portfolioPL >= 0 ? '+' : ''}₹{formatNumber(portfolioPL)} P&L
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <Link to="/portfolio" className="btn btn-primary">
                💼 Manage Portfolio
              </Link>
              <Link to="/watchlist" className="btn btn-secondary">
                ⭐ Watchlist
              </Link>
            </div>
          </div>
        </div>
      ) : isAuthenticated && !userPortfolio ? (
        <div className="card" style={{ background: 'linear-gradient(135deg, #111827 0%, #1e293b 100%)', borderColor: '#3b82f6', marginBottom: 24 }}>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>
                ⭐ Paper Trading Portfolio
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#ffffff', marginTop: 4 }}>
                No active portfolio detected
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                Initialize your paper trading portfolio to track your virtual investments.
              </div>
            </div>
            <div>
              <Link to="/portfolio" className="btn btn-primary">
                💼 Setup Portfolio
              </Link>
            </div>
          </div>
        </div>
      ) : !isAuthenticated && (
        <div className="card" style={{ background: 'linear-gradient(135deg, #111827 0%, #172554 100%)', borderColor: '#2563eb', marginBottom: 24 }}>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase' }}>
                🚀 Personalized Portfolio & Watchlist
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#ffffff', marginTop: 4 }}>
                Start Trading with ₹100,000 Paper Capital
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                Create your account to manage stock orders with database transaction integrity.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <Link to="/register" className="btn btn-primary">
                Create Free Account
              </Link>
              <Link to="/login" className="btn btn-secondary">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Market Statistics Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Companies</div>
          <div className="stat-value">{data.total_companies}</div>
          <div className="stat-sub">Nifty 50 universe</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Sectors</div>
          <div className="stat-value">{data.total_sectors}</div>
          <div className="stat-sub">Diversified industries</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Price Records</div>
          <div className="stat-value">{formatNumber(data.total_price_records, 0)}</div>
          <div className="stat-sub">TimescaleDB hypertable</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Market Cap</div>
          <div className="stat-value">₹{data.market_cap_total_trillion}T</div>
          <div className="stat-sub">Aggregated market value</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Corporate Actions</div>
          <div className="stat-value">{formatNumber(data.total_corporate_actions, 0)}</div>
          <div className="stat-sub">Dividends & stock splits</div>
        </div>
      </div>

      {/* Gainers / Losers Grid */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Top Gainers */}
        <div className="card">
          <div className="card-header">
            <h3>🟢 Top Gainers (Latest Session)</h3>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Day Return</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_gainers || []).map((s) => (
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
          <div className="card-header">
            <h3>🔴 Top Losers (Latest Session)</h3>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Day Return</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_losers || []).map((s) => (
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
        <div className="card-header">
          <h3>Sector Market Cap Distribution (₹ Trillion)</h3>
        </div>
        <div className="card-body">
          <div style={{ width: '100%', height: 360 }}>
            <ResponsiveContainer>
              <BarChart data={sectorChart} layout="vertical" margin={{ left: 140, right: 30, top: 10, bottom: 10 }}>
                <XAxis type="number" stroke="var(--text-muted)" tick={{ fontSize: 12, fill: 'var(--text-secondary)' }} />
                <YAxis type="category" dataKey="name" stroke="var(--text-muted)" tick={{ fontSize: 12, fill: 'var(--text-secondary)' }} width={130} />
                <Tooltip
                  formatter={(v) => [`₹${Number(v).toFixed(2)}T`, 'Market Cap']}
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#232e42', borderRadius: 8, color: '#fff' }}
                />
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
        <div className="card-header">
          <h3>Sector Performance Overview</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Sector</th>
                  <th className="text-center">Companies</th>
                  <th className="text-right">Market Cap (₹T)</th>
                  <th className="text-right">Avg P/E Ratio</th>
                </tr>
              </thead>
              <tbody>
                {(data.sector_breakdown || []).map((s) => (
                  <tr key={s.sector_name}>
                    <td><strong>{s.sector_name}</strong></td>
                    <td className="text-center">{s.num_companies}</td>
                    <td className="text-right text-mono">₹{formatNumber(s.total_market_cap_trillion_inr)}T</td>
                    <td className="text-right text-mono">{formatNumber(s.avg_pe_ratio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
