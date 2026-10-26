export function Loading({ message = 'Loading...' }) {
  return (
    <div className="loading-container">
      <div className="spinner" />
      <p>{message}</p>
    </div>
  )
}

export function EmptyState({ icon = '📭', message = 'No data available' }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <p>{message}</p>
    </div>
  )
}

export function ErrorState({ message = 'Something went wrong', onRetry }) {
  return (
    <div className="error-state">
      <div className="error-icon">⚠️</div>
      <p>{message}</p>
      {onRetry && (
        <button className="btn btn-primary" onClick={onRetry} style={{ marginTop: 12 }}>
          Retry
        </button>
      )}
    </div>
  )
}

export function DataDateBadge({ date }) {
  if (!date) return null
  return (
    <span className="data-date-badge">
      📅 Data as of {date}
    </span>
  )
}

export function DemoBanner() {
  return (
    <div className="demo-banner">
      ⚠️ <strong>Demo Mode</strong> — No authentication implemented. Data is shared and not user-specific.
    </div>
  )
}

export function formatNumber(n, decimals = 2) {
  if (n == null || isNaN(n)) return '—'
  return Number(n).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatLargeNumber(n) {
  if (n == null || isNaN(n)) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e12) return (n / 1e12).toFixed(2) + 'T'
  if (abs >= 1e9) return (n / 1e9).toFixed(2) + 'B'
  if (abs >= 1e7) return (n / 1e7).toFixed(2) + 'Cr'
  if (abs >= 1e5) return (n / 1e5).toFixed(2) + 'L'
  return formatNumber(n)
}

export function PctBadge({ value }) {
  if (value == null || isNaN(value)) return <span className="text-muted">—</span>
  const cls = value >= 0 ? 'positive' : 'negative'
  const sign = value >= 0 ? '+' : ''
  return <span className={cls}>{sign}{Number(value).toFixed(2)}%</span>
}
