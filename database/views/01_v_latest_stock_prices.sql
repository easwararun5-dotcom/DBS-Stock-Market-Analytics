-- ============================================================================
-- View 1: v_latest_stock_prices
-- Description: Latest available trading day price, volume, and technical snapshot per company
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Provides a clean, consolidated real-time quote view for all 49 companies.
-- Extracts each stock's most recent trading session with price action,
-- trading volume, daily return, moving averages (50 & 200 DMA), and 20-day volatility.

-- Underlying SQL Concepts:
-- 1. PostgreSQL DISTINCT ON (p.ticker) with ORDER BY p.ticker, p.trading_date DESC:
--    Guarantees exactly one most recent record per company in an efficient single scan.
-- 2. Multi-table INNER JOIN connecting daily_price_history to company and sector.
-- 3. CASE expressions for price spread and data quality flags.

CREATE OR REPLACE VIEW v_latest_stock_prices AS
SELECT DISTINCT ON (p.ticker)
    c.ticker,
    c.company_name,
    s.sector_name,
    p.trading_date AS latest_trading_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.volume,
    p.daily_return,
    ROUND(p.daily_return * 100.0, 2) AS daily_return_pct,
    p.vol_20d,
    ROUND(p.vol_20d * 100.0, 2) AS volatility_20d_pct,
    p.ma_50,
    p.ma_200,
    ROUND(p.high_price - p.low_price, 4) AS intraday_range,
    CASE 
        WHEN p.open_price > 0 THEN 
            ROUND(((p.high_price - p.low_price) / p.open_price) * 100.0, 2)
        ELSE NULL 
    END AS intraday_swing_pct
FROM daily_price_history p
INNER JOIN company c ON p.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
ORDER BY p.ticker, p.trading_date DESC;

COMMENT ON VIEW v_latest_stock_prices IS 'Latest available daily price quote, volume, and moving averages for each company.';
