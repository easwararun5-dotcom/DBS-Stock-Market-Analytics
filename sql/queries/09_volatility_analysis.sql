-- ============================================================================
-- 09_volatility_analysis.sql
-- Description: Historical price volatility, moving average crossovers, and drawdown analysis
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 9.1: Moving Average Trend and Crossover Status (50-DMA vs 200-DMA)
-- Demonstrates: Conditional trend classification based on moving averages on the latest snapshot date
-- Business Purpose: Identify stocks in bullish (Golden Cross: MA_50 > MA_200) vs bearish (Death Cross) posture.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    p.trading_date,
    p.close_price,
    p.ma_50,
    p.ma_200,
    ROUND((p.ma_50 - p.ma_200) / p.ma_200 * 100, 2) AS ma_spread_pct,
    CASE 
        WHEN p.ma_50 > p.ma_200 AND p.close_price > p.ma_50 THEN 'Strong Bullish (Price > 50MA > 200MA)'
        WHEN p.ma_50 > p.ma_200 AND p.close_price <= p.ma_50 THEN 'Bullish Pullback (50MA > 200MA)'
        WHEN p.ma_50 < p.ma_200 AND p.close_price < p.ma_50 THEN 'Strong Bearish (Price < 50MA < 200MA)'
        ELSE 'Neutral / Transition'
    END AS technical_regime
FROM daily_price_history p
INNER JOIN company c ON p.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE p.trading_date = '2026-01-30'
ORDER BY ma_spread_pct DESC;

-- Query 9.2: Lifetime Maximum High, Maximum Low, and Historical Range Expansion
-- Demonstrates: Ratio of all-time high to all-time low price in the sample
-- Business Purpose: Measure the historical volatility corridor and long-term price expansion.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    ROUND(MIN(p.low_price), 2) AS all_time_low,
    ROUND(MAX(p.high_price), 2) AS all_time_high,
    ROUND(MAX(p.high_price) / NULLIF(MIN(p.low_price), 0), 1) AS expansion_multiple,
    ROUND(AVG(p.vol_20d) * 100, 2) AS avg_realized_volatility_20d
FROM daily_price_history p
INNER JOIN company c ON p.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE p.low_price > 0 -- Filter out negative price artifacts for valid ratio calculation
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY expansion_multiple DESC
LIMIT 15;

-- Query 9.3: Monthly Trend of Market-Wide 20-Day Realized Volatility
-- Demonstrates: Date truncation (DATE_TRUNC('month', ...)), market-wide volatility aggregation
-- Business Purpose: Identify historical market turbulence regimes (e.g. 2008 Financial Crisis, 2020 Pandemic).
SELECT 
    TO_CHAR(DATE_TRUNC('month', trading_date), 'YYYY-MM') AS year_month,
    ROUND(AVG(vol_20d) * 100, 2) AS market_avg_volatility_pct,
    ROUND(MAX(vol_20d) * 100, 2) AS peak_single_stock_volatility_pct,
    COUNT(DISTINCT ticker) AS active_tickers,
    ROUND(AVG(volume) / 1e6, 2) AS avg_daily_volume_million
FROM daily_price_history
WHERE vol_20d IS NOT NULL
GROUP BY DATE_TRUNC('month', trading_date)
ORDER BY market_avg_volatility_pct DESC
LIMIT 15;

-- Query 9.4: Return Distribution and Fat-Tail Frequency Analysis
-- Demonstrates: Bucketing daily returns using CASE WHEN and counting frequency across all 287k rows
-- Business Purpose: Quantify tail-risk and positive/negative return skewness across Indian equities.
SELECT 
    CASE 
        WHEN daily_return > 0.05 THEN '1. Mega Gain (> +5%)'
        WHEN daily_return BETWEEN 0.02 AND 0.05 THEN '2. Solid Gain (+2% to +5%)'
        WHEN daily_return BETWEEN 0.00 AND 0.02 THEN '3. Modest Gain (0% to +2%)'
        WHEN daily_return BETWEEN -0.02 AND 0.00 THEN '4. Modest Loss (-2% to 0%)'
        WHEN daily_return BETWEEN -0.05 AND -0.02 THEN '5. Solid Loss (-5% to -2%)'
        ELSE '6. Mega Loss (< -5%)'
    END AS return_bracket,
    COUNT(*) AS trading_sessions_count,
    ROUND(COUNT(*) * 100.0 / (SELECT count(*) FROM daily_price_history WHERE daily_return IS NOT NULL), 2) AS percentage_of_total_sessions
FROM daily_price_history
WHERE daily_return IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- Query 9.5: Average Intraday Swing Percentage by Company
-- Demonstrates: Computing intraday high-low percentage spread relative to open price
-- Business Purpose: Screen for stocks offering the widest daily trading ranges for active trading strategies.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    ROUND(AVG((p.high_price - p.low_price) / NULLIF(p.open_price, 0)) * 100, 2) AS avg_intraday_swing_pct,
    ROUND(MAX((p.high_price - p.low_price) / NULLIF(p.open_price, 0)) * 100, 2) AS max_intraday_swing_pct,
    COUNT(*) AS trading_days
FROM daily_price_history p
INNER JOIN company c ON p.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE p.open_price > 0
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY avg_intraday_swing_pct DESC
LIMIT 15;
