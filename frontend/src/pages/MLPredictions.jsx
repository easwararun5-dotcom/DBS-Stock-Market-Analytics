import { useState, useEffect } from 'react'
import api from '../api'
import { Loading, ErrorState, formatNumber } from '../components/Common'

export default function MLPredictions() {
  const [status, setStatus] = useState(null)
  const [companies, setCompanies] = useState([])
  const [selectedTicker, setSelectedTicker] = useState('TCS.NS')
  const [inputTicker, setInputTicker] = useState('TCS.NS')
  const [prediction, setPrediction] = useState(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [loadingPred, setLoadingPred] = useState(false)
  const [error, setError] = useState(null)
  const [predError, setPredError] = useState(null)

  // Load ML status and company list
  useEffect(() => {
    Promise.all([api.mlStatus(), api.companies()])
      .then(([statusRes, compRes]) => {
        setStatus(statusRes)
        const list = compRes?.data || []
        setCompanies(list)
        if (list.length > 0) {
          const defaultTicker = list.find(c => c.ticker === 'TCS.NS')?.ticker || list[0].ticker
          setSelectedTicker(defaultTicker)
          setInputTicker(defaultTicker)
          fetchPrediction(defaultTicker)
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoadingStatus(false))
  }, [])

  const fetchPrediction = async (ticker) => {
    if (!ticker) return
    setLoadingPred(true)
    setPredError(null)
    try {
      const res = await api.mlPredict(ticker)
      setPrediction(res)
    } catch (e) {
      setPredError(e.message || 'Failed to fetch prediction.')
      setPrediction(null)
    } finally {
      setLoadingPred(false)
    }
  }

  const handleSelectChange = (e) => {
    const t = e.target.value
    setSelectedTicker(t)
    setInputTicker(t)
    fetchPrediction(t)
  }

  const handleInputChange = (e) => {
    setInputTicker(e.target.value)
  }

  const handleFormSubmit = (e) => {
    if (e) e.preventDefault()
    const clean = inputTicker.trim()
    if (!clean) return
    setSelectedTicker(clean)
    fetchPrediction(clean)
  }

  const handleQuickSelect = (t) => {
    setSelectedTicker(t)
    setInputTicker(t)
    fetchPrediction(t)
  }

  if (loadingStatus) return <Loading message="Loading ML forecasting system..." />
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />

  const getTrendBadge = (trend) => {
    if (trend === 'UP') {
      return (
        <span style={{
          background: 'rgba(16, 185, 129, 0.15)',
          color: '#10b981',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          padding: '8px 18px',
          borderRadius: 20,
          fontWeight: 700,
          fontSize: 16,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6
        }}>
          📈 UP (Bullish)
        </span>
      )
    }
    if (trend === 'DOWN') {
      return (
        <span style={{
          background: 'rgba(239, 68, 68, 0.15)',
          color: '#ef4444',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          padding: '8px 18px',
          borderRadius: 20,
          fontWeight: 700,
          fontSize: 16,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6
        }}>
          📉 DOWN (Bearish)
        </span>
      )
    }
    return (
      <span style={{
        background: 'rgba(59, 130, 246, 0.15)',
        color: '#3b82f6',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        padding: '8px 18px',
        borderRadius: 20,
        fontWeight: 700,
        fontSize: 16,
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6
      }}>
        ⚖️ NEUTRAL (Sideways)
      </span>
    )
  }

  const demoQuickTickers = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', paddingBottom: 40 }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h2>🤖 Stock Trend Forecasting</h2>
        <p>Live ML classification for 5-day directional price movement (&gt;+1.5% UP, &lt;-1.5% DOWN, or NEUTRAL)</p>
      </div>

      {/* Model Status Banner */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 16,
        marginBottom: 28,
      }}>
        <div className="card" style={{ padding: '16px 20px', background: 'var(--bg-card)' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            Model Status
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: status?.status === 'trained' ? '#10b981' : '#f59e0b' }}>
            {status?.status === 'trained' ? `Active & Trained (v${status?.model_version || '1.1.0'})` : 'Not Trained'}
          </div>
        </div>

        <div className="card" style={{ padding: '16px 20px', background: 'var(--bg-card)' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            Classifier Algorithm
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--primary)' }}>
            {status?.model_name === 'hist_gradient_boosting' ? 'Hist Gradient Boosting' : status?.model_name === 'random_forest' ? 'Random Forest (100 Trees)' : (status?.model_name || 'Class-Weighted Ensemble')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Class-Weighted Sample Loss</div>
        </div>

        <div className="card" style={{ padding: '16px 20px', background: 'var(--bg-card)' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            Forecast Horizon
          </div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>
            {status?.forecast_horizon || 5} Trading Sessions
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>Close[t+5] / Close[t] - 1</div>
        </div>

        <div className="card" style={{ padding: '16px 20px', background: 'var(--bg-card)' }}>
          <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
            Held-Out Test Accuracy
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#3b82f6' }}>
            {status?.test_accuracy ? `${(status.test_accuracy * 100).toFixed(2)}%` : '39.01%'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            Macro F1: {status?.test_macro_f1 ? status.test_macro_f1.toFixed(4) : '0.3489'}
          </div>
        </div>
      </div>

      {/* Ticker Selector Card */}
      <div className="card" style={{ padding: 24, marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h3 style={{ fontSize: 18, marginBottom: 4 }}>Select or Enter Stock Ticker</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0 }}>
              Queries live TimescaleDB technical indicators and calculates 20 technical features without lookahead bias.
            </p>
          </div>
          <form onSubmit={handleFormSubmit} style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <select
              value={companies.some(c => c.ticker === selectedTicker) ? selectedTicker : ''}
              onChange={handleSelectChange}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: 14,
                fontWeight: 500,
                minWidth: 180,
                cursor: 'pointer',
              }}
            >
              <option value="" disabled>-- Select Stock --</option>
              {companies.map(c => (
                <option key={c.ticker} value={c.ticker}>
                  {c.ticker} — {c.company_name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={inputTicker}
              onChange={handleInputChange}
              placeholder="e.g. INFY or TCS"
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                fontSize: 14,
                fontWeight: 600,
                width: 140,
                textTransform: 'uppercase',
              }}
            />
            <button
              type="submit"
              disabled={loadingPred || !inputTicker.trim()}
              className="btn btn-primary"
              style={{ padding: '8px 18px', fontWeight: 600, cursor: 'pointer' }}
            >
              {loadingPred ? 'Analyzing...' : '⚡ Predict'}
            </button>
          </form>
        </div>

        {/* Quick select demo stock chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>Quick Demo:</span>
          {demoQuickTickers.map(t => (
            <button
              key={t}
              type="button"
              onClick={() => handleQuickSelect(t)}
              style={{
                background: selectedTicker === t ? 'var(--primary-light)' : 'var(--bg-secondary)',
                color: selectedTicker === t ? 'var(--primary)' : 'var(--text-secondary)',
                border: selectedTicker === t ? '1px solid var(--primary)' : '1px solid var(--border-light)',
                borderRadius: 16,
                padding: '4px 12px',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {t.replace('.NS', '')}
            </button>
          ))}
        </div>
      </div>

      {/* Prediction Output Area */}
      {loadingPred ? (
        <Loading message={`Calculating technical features & evaluating model for ${inputTicker}...`} />
      ) : predError ? (
        <div className="card" style={{ padding: 32, textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.3)', marginBottom: 28 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
          <h4 style={{ color: '#ef4444', marginBottom: 8 }}>Forecast Unavailable</h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 16 }}>{predError}</p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
            <button
              onClick={() => handleQuickSelect('TCS.NS')}
              className="btn btn-primary"
              style={{ fontSize: 13 }}
            >
              Reset to TCS.NS
            </button>
            <button
              onClick={() => handleQuickSelect('RELIANCE.NS')}
              className="btn"
              style={{ fontSize: 13 }}
            >
              Try RELIANCE.NS
            </button>
          </div>
        </div>
      ) : prediction ? (
        <div className="card" style={{ padding: 32, marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20, marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 13, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4 }}>
                Active Stock Forecast
              </div>
              <h3 style={{ fontSize: 26, margin: '0 0 6px 0' }}>{prediction.ticker}</h3>
              <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                Latest Closing Price: <strong style={{ color: 'var(--text-primary)' }}>₹{formatNumber(prediction.latest_close_price)}</strong> on {prediction.latest_observation_date}
              </div>
            </div>
            <div>
              {getTrendBadge(prediction.predicted_trend)}
            </div>
          </div>

          {/* Probability Breakdown Bar */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
              <span>Directional Class Probabilities (5-Day Horizon)</span>
              <span style={{ color: 'var(--text-muted)' }}>Confidence: {(prediction.confidence_score * 100).toFixed(1)}%</span>
            </div>
            <div style={{
              display: 'flex',
              height: 28,
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              border: '1px solid var(--border-light)',
            }}>
              <div
                style={{
                  width: `${(prediction.probabilities?.DOWN || 0) * 100}%`,
                  background: '#ef4444',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  fontWeight: 700,
                  transition: 'width 0.4s ease',
                }}
                title={`DOWN: ${((prediction.probabilities?.DOWN || 0) * 100).toFixed(1)}%`}
              >
                {((prediction.probabilities?.DOWN || 0) * 100) > 10 ? `DOWN ${((prediction.probabilities?.DOWN || 0) * 100).toFixed(1)}%` : ''}
              </div>
              <div
                style={{
                  width: `${(prediction.probabilities?.NEUTRAL || 0) * 100}%`,
                  background: '#3b82f6',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  fontWeight: 700,
                  transition: 'width 0.4s ease',
                }}
                title={`NEUTRAL: ${((prediction.probabilities?.NEUTRAL || 0) * 100).toFixed(1)}%`}
              >
                {((prediction.probabilities?.NEUTRAL || 0) * 100) > 10 ? `NEUTRAL ${((prediction.probabilities?.NEUTRAL || 0) * 100).toFixed(1)}%` : ''}
              </div>
              <div
                style={{
                  width: `${(prediction.probabilities?.UP || 0) * 100}%`,
                  background: '#10b981',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  fontWeight: 700,
                  transition: 'width 0.4s ease',
                }}
                title={`UP: ${((prediction.probabilities?.UP || 0) * 100).toFixed(1)}%`}
              >
                {((prediction.probabilities?.UP || 0) * 100) > 10 ? `UP ${((prediction.probabilities?.UP || 0) * 100).toFixed(1)}%` : ''}
              </div>
            </div>
          </div>

          {/* 3 Detail Cards for Each Class */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 16,
            marginBottom: 24,
          }}>
            <div style={{
              padding: 16,
              borderRadius: 'var(--radius-md)',
              background: prediction.predicted_trend === 'DOWN' ? 'rgba(239, 68, 68, 0.08)' : 'var(--bg-secondary)',
              border: prediction.predicted_trend === 'DOWN' ? '2px solid #ef4444' : '1px solid var(--border-light)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ef4444' }}>🔴 DOWN (&lt; -1.5%)</span>
                {prediction.predicted_trend === 'DOWN' && (
                  <span style={{ fontSize: 10, background: '#ef4444', color: '#fff', padding: '2px 6px', borderRadius: 10, fontWeight: 700 }}>
                    PREDICTED
                  </span>
                )}
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#ef4444' }}>
                {((prediction.probabilities?.DOWN || 0) * 100).toFixed(2)}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Drop of more than 1.5% in 5 trading days
              </div>
            </div>

            <div style={{
              padding: 16,
              borderRadius: 'var(--radius-md)',
              background: prediction.predicted_trend === 'NEUTRAL' ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-secondary)',
              border: prediction.predicted_trend === 'NEUTRAL' ? '2px solid #3b82f6' : '1px solid var(--border-light)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#3b82f6' }}>🔵 NEUTRAL (±1.5%)</span>
                {prediction.predicted_trend === 'NEUTRAL' && (
                  <span style={{ fontSize: 10, background: '#3b82f6', color: '#fff', padding: '2px 6px', borderRadius: 10, fontWeight: 700 }}>
                    PREDICTED
                  </span>
                )}
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#3b82f6' }}>
                {((prediction.probabilities?.NEUTRAL || 0) * 100).toFixed(2)}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Consolidation within ±1.5% return corridor
              </div>
            </div>

            <div style={{
              padding: 16,
              borderRadius: 'var(--radius-md)',
              background: prediction.predicted_trend === 'UP' ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-secondary)',
              border: prediction.predicted_trend === 'UP' ? '2px solid #10b981' : '1px solid var(--border-light)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#10b981' }}>🟢 UP (&gt; +1.5%)</span>
                {prediction.predicted_trend === 'UP' && (
                  <span style={{ fontSize: 10, background: '#10b981', color: '#fff', padding: '2px 6px', borderRadius: 10, fontWeight: 700 }}>
                    PREDICTED
                  </span>
                )}
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#10b981' }}>
                {((prediction.probabilities?.UP || 0) * 100).toFixed(2)}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Gain of more than 1.5% in 5 trading days
              </div>
            </div>
          </div>

          {/* Model Transparency & Disclaimer Notice */}
          <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-md)',
            padding: 16,
            fontSize: 12,
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
            borderLeft: '4px solid var(--primary)',
          }}>
            <strong>Model Methodology & Disclaimer:</strong> {prediction.disclaimer} Forecast is generated by a class-weighted HistGradientBoosting classifier fitted on 227,873 historical Nifty 50 observations from 1999–2021 with strict embargo gaps.
          </div>
        </div>
      ) : null}

      {/* Model Benchmark Card */}
      <div className="card" style={{ padding: 24 }}>
        <h4 style={{ fontSize: 16, marginBottom: 16 }}>📊 Out-of-Sample Benchmark Comparison (2024–2026 Test Period)</h4>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-light)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px 12px' }}>Model</th>
                <th style={{ padding: '8px 12px' }}>Validation Accuracy</th>
                <th style={{ padding: '8px 12px' }}>Test Accuracy</th>
                <th style={{ padding: '8px 12px' }}>Test Macro F1</th>
                <th style={{ padding: '8px 12px' }}>Brier Score</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <td style={{ padding: '10px 12px' }}>Majority-Class Baseline</td>
                <td style={{ padding: '10px 12px' }}>35.57%</td>
                <td style={{ padding: '10px 12px' }}>31.96%</td>
                <td style={{ padding: '10px 12px' }}>0.1615</td>
                <td style={{ padding: '10px 12px' }}>—</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <td style={{ padding: '10px 12px' }}>Historical Momentum Baseline</td>
                <td style={{ padding: '10px 12px' }}>34.10%</td>
                <td style={{ padding: '10px 12px' }}>33.52%</td>
                <td style={{ padding: '10px 12px' }}>0.3240</td>
                <td style={{ padding: '10px 12px' }}>—</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <td style={{ padding: '10px 12px' }}>Logistic Regression (Unweighted)</td>
                <td style={{ padding: '10px 12px' }}>39.24%</td>
                <td style={{ padding: '10px 12px' }}>39.27%</td>
                <td style={{ padding: '10px 12px' }}>0.3030</td>
                <td style={{ padding: '10px 12px' }}>0.2198</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <td style={{ padding: '10px 12px' }}>Random Forest (Unweighted)</td>
                <td style={{ padding: '10px 12px' }}>40.13%</td>
                <td style={{ padding: '10px 12px' }}>39.71%</td>
                <td style={{ padding: '10px 12px' }}>0.3059</td>
                <td style={{ padding: '10px 12px' }}>0.2196</td>
              </tr>
              <tr style={{ background: 'rgba(59, 130, 246, 0.08)', fontWeight: 600 }}>
                <td style={{ padding: '10px 12px', color: 'var(--primary)' }}>HistGradientBoosting (Class-Weighted, Active)</td>
                <td style={{ padding: '10px 12px', color: 'var(--primary)' }}>39.36%</td>
                <td style={{ padding: '10px 12px', color: 'var(--primary)' }}>39.01%</td>
                <td style={{ padding: '10px 12px', color: 'var(--primary)' }}>0.3489</td>
                <td style={{ padding: '10px 12px', color: 'var(--primary)' }}>0.2203</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
