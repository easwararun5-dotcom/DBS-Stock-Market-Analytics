// API client for DBS Stock Market Analytics
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function fetchApi(endpoint, options = {}) {
  const token = localStorage.getItem('dbs_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include', // Support HttpOnly cookies
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Authentication
  register: (data) => fetchApi('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login:    (data) => fetchApi('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  logout:   ()     => fetchApi('/api/auth/logout', { method: 'POST' }),
  me:       ()     => fetchApi('/api/auth/me'),

  // Market & Core Data
  health:              ()           => fetchApi('/api/health'),
  dashboard:           (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/dashboard${q ? '?' + q : ''}`);
  },
  latestPrices:        ()           => fetchApi('/api/prices/latest'),
  priceHistory:        (ticker, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/prices/${ticker}${q ? '?' + q : ''}`);
  },
  companies:           (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/companies${q ? '?' + q : ''}`);
  },
  companyDetail:       (ticker)     => fetchApi(`/api/companies/${ticker}`),
  sectors:             ()           => fetchApi('/api/sectors'),
  summary:             (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/summary${q ? '?' + q : ''}`);
  },
  volatility:          ()           => fetchApi('/api/volatility'),
  corporateActions:    (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/corporate-actions${q ? '?' + q : ''}`);
  },
  corporateActionSummary: ()        => fetchApi('/api/corporate-actions/summary'),
  performance:         ()           => fetchApi('/api/performance'),
  timeBucket:          (ticker, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/analytics/time-bucket/${ticker}${q ? '?' + q : ''}`);
  },

  // Machine Learning
  mlStatus:            ()           => fetchApi('/api/ml/status'),
  mlPredict:           (ticker)     => fetchApi(`/api/ml/predict/${ticker}`),
  mlPredictions:       (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/ml/predictions${q ? '?' + q : ''}`);
  },

  // Portfolios (User-specific)
  portfolios:          ()           => fetchApi('/api/portfolios'),
  createPortfolio:     (data)       => fetchApi('/api/portfolios', { method: 'POST', body: JSON.stringify(data) }),
  portfolioDetail:     (id)         => fetchApi(`/api/portfolios/${id}`),
  portfolioHoldings:   (id)         => fetchApi(`/api/portfolios/${id}/holdings`),
  portfolioTransactions: (id, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/portfolios/${id}/transactions${q ? '?' + q : ''}`);
  },
  buyStock:            (id, data)   => fetchApi(`/api/portfolios/${id}/buy`, { method: 'POST', body: JSON.stringify(data) }),
  sellStock:           (id, data)   => fetchApi(`/api/portfolios/${id}/sell`, { method: 'POST', body: JSON.stringify(data) }),

  // Watchlist (User-specific)
  getWatchlist:        ()           => fetchApi('/api/watchlist'),
  addWatchlist:        (data)       => fetchApi('/api/watchlist', { method: 'POST', body: JSON.stringify(data) }),
  removeWatchlist:     (ticker)     => fetchApi(`/api/watchlist/${ticker}`, { method: 'DELETE' }),

  // Legacy fallbacks
  watchlist:           (userId)     => fetchApi(`/api/watchlist?user_id=${userId}`),
  legacyHoldings:      (userId)     => fetchApi(`/api/portfolio/holdings?user_id=${userId}`),
  legacyTransactions:  (userId, params = {}) => {
    const q = new URLSearchParams({ user_id: userId, ...params }).toString();
    return fetchApi(`/api/portfolio/transactions?${q}`);
  },
};

export default api;
