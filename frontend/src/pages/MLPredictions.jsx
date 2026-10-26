import { useState, useEffect } from 'react'
import api from '../api'
import { Loading, ErrorState } from '../components/Common'

export default function MLPredictions() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.mlStatus()
      .then(setStatus)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Checking ML status..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  return (
    <div>
      <div className="page-header">
        <h2>ML Predictions</h2>
        <p>Machine learning stock price forecasts</p>
      </div>

      <div className="ml-notice" style={{ maxWidth: 700, margin: '40px auto' }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>🤖</div>
        <h3 style={{ fontSize: 22, marginBottom: 12 }}>
          {status?.status === 'not_trained'
            ? 'Model Not Trained Yet'
            : `${status?.total_predictions || 0} Predictions Available`
          }
        </h3>
        <p style={{ marginBottom: 16, lineHeight: 1.8 }}>
          {status?.message}
        </p>

        {status?.status === 'not_trained' && (
          <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-md)',
            padding: 20,
            marginTop: 16,
            textAlign: 'left',
          }}>
            <h4 style={{ fontSize: 14, marginBottom: 12, color: 'var(--text-primary)' }}>
              📋 ML Pipeline — Implementation Plan
            </h4>
            <ul style={{ paddingLeft: 20, color: 'var(--text-secondary)', fontSize: 13, lineHeight: 2 }}>
              <li>Feature engineering from daily_price_history (returns, moving averages, volatility)</li>
              <li>Train/validation/test split with proper temporal ordering</li>
              <li>Model training (e.g., LSTM, XGBoost, or Prophet)</li>
              <li>Evaluation metrics (MAE, RMSE, directional accuracy)</li>
              <li>Store predictions in ml_prediction table</li>
              <li>Connect this UI to display real forecasts with confidence intervals</li>
            </ul>
            <p style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              This section will be implemented separately. No fake predictions are shown.
            </p>
          </div>
        )}

        <div style={{
          display: 'flex',
          gap: 16,
          justifyContent: 'center',
          marginTop: 24,
          flexWrap: 'wrap',
        }}>
          <StatusCard
            label="Model Status"
            value={status?.status === 'not_trained' ? 'Not Trained' : 'Trained'}
            color={status?.status === 'not_trained' ? 'var(--warning)' : 'var(--success)'}
          />
          <StatusCard
            label="Predictions"
            value={status?.total_predictions || 0}
            color="var(--primary)"
          />
          <StatusCard
            label="Schema"
            value="Ready"
            color="var(--success)"
          />
        </div>
      </div>
    </div>
  )
}

function StatusCard({ label, value, color }) {
  return (
    <div style={{
      background: 'var(--bg-primary)',
      border: '1px solid var(--border-light)',
      borderRadius: 'var(--radius-md)',
      padding: '16px 24px',
      textAlign: 'center',
      minWidth: 140,
    }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
    </div>
  )
}
