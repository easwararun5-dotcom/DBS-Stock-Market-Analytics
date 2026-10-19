-- ============================================================================
-- View 5: v_stock_volatility
-- Description: Latest volatility indicators and moving averages per ticker
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Extracts the most recent trading day's 20-day volatility, 50-day MA, and 200-day MA
-- for each company. Also surfaces the long-term volatility from stock_summary for
-- comparison, allowing both a point-in-time and historical volatility perspective.
-- NULLs are preserved where indicators could not be computed (e.g. insufficient history).

-- Underlying SQL Concepts:
-- 1. DISTINCT ON (ticker) with ORDER BY ticker, trading_date DESC to efficiently
--    select each ticker's most recent row in a single scan.
-- 2. LEFT JOIN to stock_summary to include long-term volatility even for tickers
--    whose latest price row has NULL technical indicators.
-- 3. CASE expression to classify volatility regime.

CREATE OR REPLACE VIEW v_stock_volatility AS
SELECT DISTINCT ON (dph.ticker)
    c.ticker,
    c.company_name,
    s.sector_name,
    dph.trading_date                                AS latest_date,
    dph.close_price                                 AS latest_close,
    dph.daily_return,
    ROUND(dph.daily_return * 100.0, 2)              AS daily_return_pct,
    dph.vol_20d,
    ROUND(dph.vol_20d * 100.0, 2)                  AS volatility_20d_pct,
    dph.ma_50,
    dph.ma_200,
    -- Moving average crossover signal
    CASE
        WHEN dph.ma_50 IS NULL OR dph.ma_200 IS NULL THEN 'Insufficient Data'
        WHEN dph.ma_50 > dph.ma_200 THEN 'Bullish (MA50 > MA200)'
        WHEN dph.ma_50 < dph.ma_200 THEN 'Bearish (MA50 < MA200)'
        ELSE 'Neutral (MA50 = MA200)'
    END AS ma_crossover_signal,
    -- Price vs moving averages
    CASE
        WHEN dph.close_price IS NULL OR dph.ma_50 IS NULL THEN NULL
        WHEN dph.close_price > dph.ma_50 THEN 'Above MA50'
        ELSE 'Below MA50'
    END AS price_vs_ma50,
    -- Long-term volatility from summary for comparison
    ss.volatility_pct                               AS historical_volatility_pct
FROM daily_price_history dph
JOIN company c ON c.ticker = dph.ticker
JOIN sector s ON s.sector_id = c.sector_id
LEFT JOIN stock_summary ss ON ss.ticker = dph.ticker
ORDER BY dph.ticker, dph.trading_date DESC;

COMMENT ON VIEW v_stock_volatility IS 'Latest 20-day volatility, 50/200-day moving averages, and MA crossover signal per ticker.';
