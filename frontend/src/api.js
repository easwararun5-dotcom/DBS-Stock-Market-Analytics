// API client for DBS Stock Market Analytics
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function fetchApi(endpoint) {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

export const api = {
  health:              ()           => fetchApi('/api/health'),
  dashboard:           ()           => fetchApi('/api/dashboard'),
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
  mlStatus:            ()           => fetchApi('/api/ml/status'),
  mlPredictions:       (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return fetchApi(`/api/ml/predictions${q ? '?' + q : ''}`);
  },
  watchlist:           (userId)     => fetchApi(`/api/watchlist?user_id=${userId}`),
  portfolioHoldings:   (userId)     => fetchApi(`/api/portfolio/holdings?user_id=${userId}`),
  portfolioTransactions: (userId, params = {}) => {
    const q = new URLSearchParams({ user_id: userId, ...params }).toString();
    return fetchApi(`/api/portfolio/transactions?${q}`);
  },
};

export default api;
