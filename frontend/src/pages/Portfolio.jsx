import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { Loading, ErrorState, EmptyState, formatNumber, PctBadge } from '../components/Common';

const PIE_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
  '#06b6d4', '#14b8a6', '#f97316', '#6366f1', '#84cc16'
];

export default function Portfolio() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('holdings');

  // Modal States
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [showSellModal, setShowSellModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Buy Form
  const [buyTicker, setBuyTicker] = useState('RELIANCE.NS');
  const [buyQuantity, setBuyQuantity] = useState(10);
  const [buyPrice, setBuyPrice] = useState(2500);
  const [buyNotes, setBuyNotes] = useState('');

  // Sell Form
  const [sellTicker, setSellTicker] = useState('');
  const [sellHolding, setSellHolding] = useState(null);
  const [sellQuantity, setSellQuantity] = useState(1);
  const [sellPrice, setSellPrice] = useState(0);
  const [sellNotes, setSellNotes] = useState('');

  // Create Portfolio Form
  const [newPortfolioName, setNewPortfolioName] = useState('');
  const [newPortfolioCash, setNewPortfolioCash] = useState(100000);

  // Load portfolios and companies on mount
  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    loadInitialData();
  }, [isAuthenticated]);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [portfoliosRes, pricesRes] = await Promise.all([
        api.portfolios(),
        api.latestPrices().catch(() => api.companies({ limit: 100 })),
      ]);

      const portList = portfoliosRes.data || [];
      setPortfolios(portList);
      setCompanies(pricesRes.data || []);

      if (portList.length > 0) {
        const savedPid = parseInt(localStorage.getItem('dbs_active_portfolio_id'));
        const matched = portList.find((p) => p.portfolio_id === savedPid);
        const activeId = matched ? matched.portfolio_id : portList[0].portfolio_id;
        setSelectedPortfolioId(activeId);
        localStorage.setItem('dbs_active_portfolio_id', activeId);
        await loadPortfolioDetails(activeId);
      } else {
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const loadPortfolioDetails = async (portId) => {
    try {
      const [detailRes, holdingsRes, transRes] = await Promise.all([
        api.portfolioDetail(portId),
        api.portfolioHoldings(portId),
        api.portfolioTransactions(portId, { limit: 50 }),
      ]);

      const pData = detailRes?.portfolio || detailRes;
      setPortfolioData(pData);
      setHoldings(holdingsRes?.holdings || holdingsRes?.data || []);
      setTransactions(transRes?.data || transRes?.transactions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePortfolioChange = (e) => {
    const portId = parseInt(e.target.value);
    setSelectedPortfolioId(portId);
    localStorage.setItem('dbs_active_portfolio_id', portId);
    setLoading(true);
    loadPortfolioDetails(portId);
  };

  const handleCreatePortfolio = async (e) => {
    e.preventDefault();
    setActionError(null);
    setActionLoading(true);
    try {
      const initialCash = parseFloat(newPortfolioCash) || 100000;
      const res = await api.createPortfolio({
        portfolio_name: newPortfolioName,
        initial_cash: initialCash,
        cash_balance: initialCash,
      });
      setShowCreateModal(false);
      setNewPortfolioName('');

      const newPid = res.portfolio?.portfolio_id || res.portfolio_id;
      const updatedList = await api.portfolios();
      setPortfolios(updatedList.data || []);

      if (newPid) {
        setSelectedPortfolioId(newPid);
        localStorage.setItem('dbs_active_portfolio_id', newPid);
        await loadPortfolioDetails(newPid);
      }
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Open Buy modal and autofill latest market price
  const openBuy = (ticker = 'RELIANCE.NS') => {
    setActionError(null);
    setBuyTicker(ticker);
    const comp = companies.find((c) => c.ticker === ticker);
    const p = comp && (comp.close_price || comp.latest_price) ? (comp.close_price || comp.latest_price) : 2500;
    setBuyPrice(p);
    setBuyQuantity(10);
    setBuyNotes('');
    setShowBuyModal(true);
  };

  const handleBuyTickerChange = (t) => {
    setBuyTicker(t);
    const comp = companies.find((c) => c.ticker === t);
    if (comp) {
      const p = comp.close_price || comp.latest_price;
      if (p) setBuyPrice(p);
    }
  };

  // Open Sell modal
  const openSell = (h) => {
    setActionError(null);
    setSellHolding(h);
    setSellTicker(h.ticker);
    const owned = parseFloat(h.quantity) || 1;
    setSellQuantity(Math.min(5, owned));
    setSellPrice(h.current_price || h.average_buy_price || h.avg_purchase_price || 100);
    setSellNotes('');
    setShowSellModal(true);
  };

  // Calculated KPI values
  const cashBalance = portfolioData ? parseFloat(portfolioData.cash_balance) || 0 : 0;
  const totalInvested = holdings.reduce((s, h) => s + (parseFloat(h.invested_value) || 0), 0);
  const totalCurrent = holdings.reduce((s, h) => {
    const qty = parseFloat(h.quantity) || 0;
    const price = parseFloat(h.current_price) || parseFloat(h.average_buy_price) || 0;
    return s + (parseFloat(h.current_value) || (qty * price) || 0);
  }, 0);
  const totalPortfolioValue = cashBalance + totalCurrent;
  const totalUnrealizedPL = totalCurrent - totalInvested;
  const totalUnrealizedPLPct = totalInvested > 0 ? (totalUnrealizedPL / totalInvested) * 100 : 0;

  // Realized P&L from transaction audit ledger
  const totalRealizedPL = transactions.reduce((acc, tx) => {
    if (tx.transaction_type === 'SELL') {
      const holding = holdings.find((h) => h.ticker === tx.ticker);
      const costBasis = holding ? parseFloat(holding.average_buy_price || holding.avg_purchase_price || 0) : 0;
      const proceeds = parseFloat(tx.total_amount || tx.total_value || (tx.price * tx.quantity)) || 0;
      const cost = costBasis * (parseFloat(tx.quantity) || 0);
      return acc + (costBasis > 0 ? (proceeds - cost) : 0);
    }
    return acc;
  }, 0);

  // Buy modal calculations
  const parsedBuyQty = parseFloat(buyQuantity) || 0;
  const parsedBuyPrice = parseFloat(buyPrice) || 0;
  const buyCost = Math.round(parsedBuyQty * parsedBuyPrice * 100) / 100;
  const buyRemainingCash = Math.round((cashBalance - buyCost) * 100) / 100;
  const hasInsufficientCash = buyCost > cashBalance;
  const isBuyValid = parsedBuyQty > 0 && parsedBuyPrice > 0 && !hasInsufficientCash;

  const handleBuySubmit = async (e) => {
    e.preventDefault();
    if (!isBuyValid) return;

    setActionError(null);
    setActionLoading(true);
    try {
      await api.buyStock(selectedPortfolioId, {
        ticker: buyTicker,
        quantity: parsedBuyQty,
        price: parsedBuyPrice,
        notes: buyNotes || 'Paper trading buy order',
      });
      setShowBuyModal(false);
      // Reload both details and portfolios list for sync
      await Promise.all([
        loadPortfolioDetails(selectedPortfolioId),
        api.portfolios().then((res) => setPortfolios(res.data || [])),
      ]);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Sell modal calculations
  const parsedSellQty = parseFloat(sellQuantity) || 0;
  const parsedSellPrice = parseFloat(sellPrice) || 0;
  const sellProceeds = Math.round(parsedSellQty * parsedSellPrice * 100) / 100;
  const ownedShares = sellHolding ? parseFloat(sellHolding.quantity) : 0;
  const sellCashAfter = Math.round((cashBalance + sellProceeds) * 100) / 100;
  const isSellValid = parsedSellQty > 0 && parsedSellQty <= ownedShares && parsedSellPrice > 0;

  const handleSellSubmit = async (e) => {
    e.preventDefault();
    if (!isSellValid) return;

    setActionError(null);
    setActionLoading(true);
    try {
      await api.sellStock(selectedPortfolioId, {
        ticker: sellTicker,
        quantity: parsedSellQty,
        price: parsedSellPrice,
        notes: sellNotes || 'Paper trading sell order',
      });
      setShowSellModal(false);
      await Promise.all([
        loadPortfolioDetails(selectedPortfolioId),
        api.portfolios().then((res) => setPortfolios(res.data || [])),
      ]);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div>
        <div className="page-header">
          <h2>Portfolio Management</h2>
          <p>Multi-portfolio tracking, real-time holdings & transaction ledger</p>
        </div>
        <div className="empty-state" style={{ maxWidth: 600, margin: '40px auto' }}>
          <div className="empty-icon">🔐</div>
          <h3 style={{ color: '#fff', marginBottom: 8 }}>Authentication Required</h3>
          <p className="empty-message">
            Sign in or register to manage your personal stock portfolios, execute database-backed paper buy/sell orders with real cash accounting, and audit transaction histories.
          </p>
          <div className="empty-action" style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <Link to="/login" className="btn btn-primary btn-lg">
              Sign In to Your Portfolio
            </Link>
            <Link to="/register" className="btn btn-secondary btn-lg">
              Create New Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) return <Loading message="Loading your portfolios and holdings..." />;
  if (error) return <ErrorState message={error} onRetry={() => loadPortfolioDetails(selectedPortfolioId)} />;

  const pieData = holdings.map((h) => ({
    name: h.ticker,
    value: parseFloat(h.current_value) || parseFloat(h.invested_value) || 0,
  }));

  return (
    <div>
      {/* Page Header with Paper Trading Badge & Portfolio Selector */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <h2>Portfolio Overview</h2>
            <span className="badge-paper-trading">
              <span className="pulse-dot"></span>
              Paper Trading Simulation
            </span>
          </div>
          <p>Real-time asset allocation, holdings performance & transaction auditing</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {portfolios.length > 0 && (
            <select
              className="form-input"
              style={{ width: 'auto', minWidth: 180, fontWeight: 600 }}
              value={selectedPortfolioId || ''}
              onChange={handlePortfolioChange}
            >
              {portfolios.map((p) => (
                <option key={p.portfolio_id} value={p.portfolio_id}>
                  📁 {p.portfolio_name}
                </option>
              ))}
            </select>
          )}
          <button className="btn btn-secondary" onClick={() => setShowCreateModal(true)}>
            + New Portfolio
          </button>
          <button className="btn btn-primary" onClick={() => openBuy()}>
            + Buy Stock
          </button>
        </div>
      </div>

      {/* Paper Trading Information Banner */}
      <div className="paper-trading-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24 }}>💡</span>
          <div className="paper-trading-banner-text">
            <strong>Virtual Paper-Trading Environment:</strong> Every newly registered account receives ₹100,000 in virtual starting capital. All orders execute against real-time NSE market prices with atomic balance updates and audit logging. No real money or brokerage accounts are involved.
          </div>
        </div>
        <div style={{ whiteSpace: 'nowrap', textAlign: 'right' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block' }}>Active Portfolio</span>
          <strong style={{ color: '#38bdf8', fontSize: 13 }}>
            {portfolioData ? portfolioData.portfolio_name : 'Default'}
          </strong>
        </div>
      </div>

      {/* Financial KPI Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
        <div className="stat-card">
          <div className="stat-label">Total Net Worth</div>
          <div className="stat-value">₹{formatNumber(totalPortfolioValue)}</div>
          <div className="stat-sub">Holdings + Virtual Cash</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Available Virtual Cash</div>
          <div className="stat-value" style={{ color: '#38bdf8' }}>₹{formatNumber(cashBalance)}</div>
          <div className="stat-sub">Ready for new paper orders</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Invested Cost Basis</div>
          <div className="stat-value">₹{formatNumber(totalInvested)}</div>
          <div className="stat-sub">{holdings.length} active positions</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Current Market Value</div>
          <div className="stat-value">₹{formatNumber(totalCurrent)}</div>
          <div className="stat-sub">Live position valuation</div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Total Unrealized P&L</div>
          <div className="stat-value">
            <span className={totalUnrealizedPL >= 0 ? 'positive' : 'negative'}>
              {totalUnrealizedPL >= 0 ? '+' : ''}₹{formatNumber(totalUnrealizedPL)}
            </span>
          </div>
          <div className="stat-sub">
            <PctBadge value={totalUnrealizedPLPct} /> return on cost
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Realized P&L</div>
          <div className="stat-value">
            <span className={totalRealizedPL >= 0 ? 'positive' : 'negative'}>
              {totalRealizedPL >= 0 ? '+' : ''}₹{formatNumber(totalRealizedPL)}
            </span>
          </div>
          <div className="stat-sub">From closed positions</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-nav">
        <button
          className={`tab-btn ${tab === 'holdings' ? 'active' : ''}`}
          onClick={() => setTab('holdings')}
        >
          Holdings ({holdings.length})
        </button>
        <button
          className={`tab-btn ${tab === 'allocation' ? 'active' : ''}`}
          onClick={() => setTab('allocation')}
        >
          Asset Allocation
        </button>
        <button
          className={`tab-btn ${tab === 'transactions' ? 'active' : ''}`}
          onClick={() => setTab('transactions')}
        >
          Audit Ledger ({transactions.length})
        </button>
      </div>

      {/* TAB 1: Holdings Table */}
      {tab === 'holdings' && (
        <>
          {holdings.length === 0 ? (
            <EmptyState
              icon="💼"
              message="Your portfolio has no active stock holdings yet. Use your virtual cash balance to execute your first paper-trade buy order."
              action={
                <button className="btn btn-primary" onClick={() => openBuy()}>
                  + Buy Your First Stock
                </button>
              }
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
                        <th className="text-right">Shares</th>
                        <th className="text-right">Avg Cost</th>
                        <th className="text-right">Market Price</th>
                        <th className="text-right">Invested Value</th>
                        <th className="text-right">Current Value</th>
                        <th className="text-right">Unrealized P&L</th>
                        <th className="text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {holdings.map((h) => {
                        const pl = parseFloat(h.unrealized_pl || h.profit_loss) || 0;
                        const plPct = parseFloat(h.unrealized_pl_pct || h.profit_loss_pct) || 0;
                        const avgCost = parseFloat(h.average_buy_price || h.avg_purchase_price) || 0;
                        const currPrice = parseFloat(h.current_price) || avgCost;

                        return (
                          <tr key={h.holding_id}>
                            <td
                              className="ticker-link"
                              style={{ cursor: 'pointer' }}
                              onClick={() => navigate(`/stocks/${h.ticker}`)}
                            >
                              {h.ticker}
                            </td>
                            <td>{h.company_name}</td>
                            <td className="text-right text-mono" style={{ fontWeight: 600 }}>
                              {h.quantity}
                            </td>
                            <td className="text-right text-mono">₹{formatNumber(avgCost)}</td>
                            <td className="text-right text-mono">₹{formatNumber(currPrice)}</td>
                            <td className="text-right text-mono">₹{formatNumber(h.invested_value)}</td>
                            <td className="text-right text-mono" style={{ fontWeight: 600 }}>
                              ₹{formatNumber(h.current_value)}
                            </td>
                            <td className="text-right text-mono">
                              <span className={pl >= 0 ? 'positive' : 'negative'}>
                                {pl >= 0 ? '+' : ''}₹{formatNumber(pl)} ({plPct >= 0 ? '+' : ''}{plPct.toFixed(2)}%)
                              </span>
                            </td>
                            <td className="text-right">
                              <div style={{ display: 'inline-flex', gap: 6 }}>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => openBuy(h.ticker)}
                                  title="Buy More Shares"
                                >
                                  + Buy
                                </button>
                                <button
                                  className="btn btn-danger btn-sm"
                                  onClick={() => openSell(h)}
                                  title="Sell Shares"
                                >
                                  - Sell
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* TAB 2: Asset Allocation */}
      {tab === 'allocation' && (
        <div className="card">
          <div className="card-header">
            <h3>Asset Allocation & Weightings</h3>
          </div>
          <div className="card-body">
            {holdings.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 40 }}>
                No holdings to visualize. Add stocks to view asset breakdown.
              </p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-around', minHeight: 340 }}>
                <ResponsiveContainer width="100%" height={320}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={120}
                      paddingAngle={3}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val) => `₹${formatNumber(val)}`}
                      contentStyle={{ backgroundColor: '#111827', borderColor: '#232e42', borderRadius: 8, color: '#fff' }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Audit Ledger */}
      {tab === 'transactions' && (
        <div className="card">
          <div className="card-header">
            <h3>Audit Ledger (PostgreSQL portfolio_transaction)</h3>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {transactions.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 40 }}>
                No transactions recorded yet.
              </p>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>TX ID</th>
                      <th>Type</th>
                      <th>Ticker</th>
                      <th className="text-right">Shares</th>
                      <th className="text-right">Price Executed</th>
                      <th className="text-right">Total Net Value</th>
                      <th>Executed At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => (
                      <tr key={tx.transaction_id}>
                        <td className="text-mono" style={{ color: 'var(--text-muted)' }}>#{tx.transaction_id}</td>
                        <td>
                          <span className={`badge ${tx.transaction_type === 'BUY' ? 'badge-positive' : 'badge-negative'}`}>
                            {tx.transaction_type}
                          </span>
                        </td>
                        <td className="ticker-link">{tx.ticker}</td>
                        <td className="text-right text-mono">{tx.quantity}</td>
                        <td className="text-right text-mono">₹{formatNumber(tx.price)}</td>
                        <td className="text-right text-mono" style={{ fontWeight: 600 }}>
                          ₹{formatNumber(tx.total_amount || tx.total_value)}
                        </td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                          {tx.executed_at || tx.transaction_date ? new Date(tx.executed_at || tx.transaction_date).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* BUY MODAL */}
      {showBuyModal && (
        <div className="modal-overlay" onClick={() => setShowBuyModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0 }}>Execute Stock Purchase (BUY)</h3>
                <span style={{ fontSize: 12, color: '#38bdf8' }}>
                  Portfolio: {portfolioData?.portfolio_name || 'Main Portfolio'}
                </span>
              </div>
              <button className="modal-close-btn" onClick={() => setShowBuyModal(false)}>×</button>
            </div>
            <form onSubmit={handleBuySubmit}>
              <div className="modal-body">
                {actionError && (
                  <div className="auth-alert error" style={{ marginBottom: 16 }}>
                    <span>⚠️ {actionError}</span>
                  </div>
                )}

                {hasInsufficientCash && (
                  <div className="auth-alert error" style={{ marginBottom: 16 }}>
                    <span>⚠️ Insufficient virtual funds. Outlay (₹{formatNumber(buyCost)}) exceeds available cash (₹{formatNumber(cashBalance)}).</span>
                  </div>
                )}

                <div className="form-group">
                  <label>Select Stock / Company</label>
                  <select
                    className="form-input"
                    value={buyTicker}
                    onChange={(e) => handleBuyTickerChange(e.target.value)}
                  >
                    {companies.map((c) => {
                      const p = c.close_price || c.latest_price;
                      return (
                        <option key={c.ticker} value={c.ticker}>
                          {c.ticker} — {c.company_name} {p ? `(₹${formatNumber(p)})` : ''}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Quantity (Shares)</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      className="form-input"
                      value={buyQuantity}
                      onChange={(e) => setBuyQuantity(e.target.value)}
                      required
                    />
                    <div className="quick-qty-group">
                      {[5, 10, 25, 50].map((qty) => (
                        <button
                          key={qty}
                          type="button"
                          className="quick-qty-btn"
                          onClick={() => setBuyQuantity(qty)}
                        >
                          {qty}
                        </button>
                      ))}
                      {parsedBuyPrice > 0 && (
                        <button
                          type="button"
                          className="quick-qty-btn"
                          style={{ color: '#38bdf8' }}
                          onClick={() => setBuyQuantity(Math.max(1, Math.floor(cashBalance / parsedBuyPrice)))}
                          title="Max Affordable"
                        >
                          Max
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Execution Price (₹)</label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="form-input"
                      value={buyPrice}
                      onChange={(e) => setBuyPrice(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Trade Notes (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Long term paper investment"
                    value={buyNotes}
                    onChange={(e) => setBuyNotes(e.target.value)}
                  />
                </div>

                {/* Real-time Order Summary */}
                <div style={{ background: 'var(--bg-tertiary)', padding: 14, borderRadius: 8, marginTop: 14, border: '1px solid var(--border)' }}>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Available Virtual Cash:</span>
                    <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                      ₹{formatNumber(cashBalance)}
                    </strong>
                  </div>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Total Trade Outlay:</span>
                    <strong style={{ color: '#fff', fontFamily: 'var(--font-mono)' }}>
                      ₹{formatNumber(buyCost)}
                    </strong>
                  </div>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Remaining Cash After Trade:</span>
                    <strong style={{ color: buyRemainingCash >= 0 ? 'var(--success)' : 'var(--danger)', fontFamily: 'var(--font-mono)' }}>
                      ₹{formatNumber(buyRemainingCash)}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowBuyModal(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-success"
                  disabled={actionLoading || !isBuyValid}
                >
                  {actionLoading ? 'Executing Order...' : 'Confirm Buy Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SELL MODAL */}
      {showSellModal && (
        <div className="modal-overlay" onClick={() => setShowSellModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0 }}>Record Stock Sale (SELL)</h3>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Available to Sell: {ownedShares} shares
                </span>
              </div>
              <button className="modal-close-btn" onClick={() => setShowSellModal(false)}>×</button>
            </div>
            <form onSubmit={handleSellSubmit}>
              <div className="modal-body">
                {actionError && (
                  <div className="auth-alert error" style={{ marginBottom: 16 }}>
                    <span>⚠️ {actionError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label>Selling Stock</label>
                  <input
                    type="text"
                    className="form-input"
                    value={sellTicker}
                    disabled
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label>Quantity to Sell (Max {ownedShares})</label>
                    <input
                      type="number"
                      min="1"
                      max={ownedShares}
                      step="1"
                      className="form-input"
                      value={sellQuantity}
                      onChange={(e) => setSellQuantity(e.target.value)}
                      required
                    />
                    <div className="quick-qty-group">
                      {ownedShares >= 2 && (
                        <button
                          type="button"
                          className="quick-qty-btn"
                          onClick={() => setSellQuantity(Math.floor(ownedShares / 2))}
                        >
                          50%
                        </button>
                      )}
                      <button
                        type="button"
                        className="quick-qty-btn"
                        onClick={() => setSellQuantity(ownedShares)}
                      >
                        All ({ownedShares})
                      </button>
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Selling Price (₹)</label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="form-input"
                      value={sellPrice}
                      onChange={(e) => setSellPrice(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Trade Notes (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Taking profits on paper trade"
                    value={sellNotes}
                    onChange={(e) => setSellNotes(e.target.value)}
                  />
                </div>

                <div style={{ background: 'var(--bg-tertiary)', padding: 14, borderRadius: 8, marginTop: 14, border: '1px solid var(--border)' }}>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Current Cash:</span>
                    <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                      ₹{formatNumber(cashBalance)}
                    </strong>
                  </div>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Sale Proceeds Credited:</span>
                    <strong style={{ color: 'var(--success)', fontFamily: 'var(--font-mono)' }}>
                      +₹{formatNumber(sellProceeds)}
                    </strong>
                  </div>
                  <div className="cash-summary-row">
                    <span style={{ color: 'var(--text-secondary)' }}>Cash Balance After Sale:</span>
                    <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                      ₹{formatNumber(sellCashAfter)}
                    </strong>
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowSellModal(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={actionLoading || !isSellValid}
                >
                  {actionLoading ? 'Recording Sale...' : 'Confirm Sale Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE PORTFOLIO MODAL */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Portfolio</h3>
              <button className="modal-close-btn" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreatePortfolio}>
              <div className="modal-body">
                {actionError && (
                  <div className="auth-alert error">
                    <span>⚠️ {actionError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label>Portfolio Name</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Tech Growth Portfolio"
                    value={newPortfolioName}
                    onChange={(e) => setNewPortfolioName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>

                <div className="form-group">
                  <label>Starting Virtual Cash Balance (₹)</label>
                  <input
                    type="number"
                    min="1000"
                    step="1000"
                    className="form-input"
                    value={newPortfolioCash}
                    onChange={(e) => setNewPortfolioCash(e.target.value)}
                    required
                  />
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Standard paper trading initial funding is ₹100,000.
                  </span>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Creating...' : 'Create Portfolio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
