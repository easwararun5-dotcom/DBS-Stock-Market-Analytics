-- ============================================================================
-- Project: DBS – Stock Market Analytics and Portfolio Management System
-- Database: stock_market_db (PostgreSQL 17/18) & stock_timescale_db (TimescaleDB)
-- Description: Representative Analytical and Operational SQL Queries
-- ============================================================================

-- ============================================================================
-- 1. BASIC FILTERING & PROJECTION
-- ============================================================================

-- 1.1 List blue-chip companies sorted by ticker
SELECT ticker, company_name, sector_id
FROM company
ORDER BY ticker ASC
LIMIT 10;

-- 1.2 Valuation screen: Companies with attractive P/E multiples
SELECT ticker, pe_ratio, forward_pe, price_to_book, dividend_yield, market_cap
FROM current_fundamentals
WHERE pe_ratio IS NOT NULL AND pe_ratio < 25.0
ORDER BY pe_ratio ASC;


-- ============================================================================
-- 2. MULTI-TABLE JOINS (INNER, LEFT, THREE-WAY)
-- ============================================================================

-- 2.1 Three-Way Join: Company fundamentals mapped to industrial sector
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.pe_ratio,
    f.market_cap,
    f.dividend_yield
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
LEFT JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY f.market_cap DESC NULLS LAST
LIMIT 10;

-- 2.2 User Portfolio Holdings with Current Market Valuation Join
SELECT 
    p.portfolio_name,
    u.username,
    h.ticker,
    c.company_name,
    h.quantity,
    h.average_buy_price,
    h.invested_value,
    COALESCE(lp.close_price, h.average_buy_price) AS current_price,
    ROUND(h.quantity * COALESCE(lp.close_price, h.average_buy_price), 2) AS current_market_value,
    ROUND(
        ((h.quantity * COALESCE(lp.close_price, h.average_buy_price)) - h.invested_value), 2
    ) AS unrealized_profit_loss
FROM portfolio_holding h
JOIN user_portfolio p ON h.portfolio_id = p.portfolio_id
JOIN app_user u ON p.user_id = u.user_id
JOIN company c ON h.ticker = c.ticker
LEFT JOIN v_latest_stock_prices lp ON h.ticker = lp.ticker
ORDER BY p.portfolio_id, h.ticker;


-- ============================================================================
-- 3. AGGREGATION & GROUP BY / HAVING
-- ============================================================================

-- 3.1 Sector-Level Summary: Aggregated Market Cap & Average Multiples
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS company_count,
    ROUND(AVG(f.pe_ratio), 2) AS avg_pe_ratio,
    ROUND(AVG(f.dividend_yield), 2) AS avg_dividend_yield,
    SUM(f.market_cap) AS total_market_cap
FROM sector s
JOIN company c ON s.sector_id = c.sector_id
LEFT JOIN current_fundamentals f ON c.ticker = f.ticker
GROUP BY s.sector_name
HAVING COUNT(c.ticker) >= 2
ORDER BY total_market_cap DESC NULLS LAST;

-- 3.2 Total Dividends Distributed by Company
SELECT 
    ca.ticker,
    c.company_name,
    COUNT(*) AS dividend_events_count,
    ROUND(SUM(ca.action_value), 2) AS cumulative_dividend_per_share
FROM corporate_action ca
JOIN company c ON ca.ticker = c.ticker
WHERE ca.action_type = 'Dividend'
GROUP BY ca.ticker, c.company_name
HAVING COUNT(*) >= 5
ORDER BY cumulative_dividend_per_share DESC;


-- ============================================================================
-- 4. SUBQUERIES & CORRELATED SUBQUERIES
-- ============================================================================

-- 4.1 Companies Trading at a P/E Ratio Below Their Sector Average
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.pe_ratio,
    ROUND(sec_avg.avg_sector_pe, 2) AS sector_avg_pe
FROM company c
JOIN sector s ON c.sector_id = s.sector_id
JOIN current_fundamentals f ON c.ticker = f.ticker
JOIN (
    SELECT c2.sector_id, AVG(f2.pe_ratio) AS avg_sector_pe
    FROM company c2
    JOIN current_fundamentals f2 ON c2.ticker = f2.ticker
    WHERE f2.pe_ratio IS NOT NULL
    GROUP BY c2.sector_id
) sec_avg ON c.sector_id = sec_avg.sector_id
WHERE f.pe_ratio < sec_avg.avg_sector_pe
ORDER BY s.sector_name, f.pe_ratio ASC;

-- 4.2 Correlated Subquery: Latest 3 Corporate Actions per Company
SELECT 
    ca.ticker,
    ca.action_date,
    ca.action_type,
    ca.action_value
FROM corporate_action ca
WHERE ca.action_date >= (
    SELECT COALESCE(MIN(sub.action_date), '2000-01-01'::DATE)
    FROM (
        SELECT action_date 
        FROM corporate_action sub
        WHERE sub.ticker = ca.ticker
        ORDER BY action_date DESC
        LIMIT 3
    ) sub
)
ORDER BY ca.ticker, ca.action_date DESC;


-- ============================================================================
-- 5. ANALYTICAL WINDOW FUNCTIONS
-- ============================================================================

-- 5.1 Market Cap Rank Within Sector (DENSE_RANK)
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.market_cap,
    DENSE_RANK() OVER (
        PARTITION BY c.sector_id 
        ORDER BY f.market_cap DESC NULLS LAST
    ) AS sector_market_cap_rank
FROM company c
JOIN sector s ON c.sector_id = s.sector_id
JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY s.sector_name, sector_market_cap_rank;

-- 5.2 Rolling 5-Day Moving Average and Day-over-Day Return (LAG)
SELECT 
    ticker,
    trading_date,
    close_price,
    ROUND(AVG(close_price) OVER (
        PARTITION BY ticker 
        ORDER BY trading_date 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_5d_ma,
    ROUND(
        (close_price - LAG(close_price, 1) OVER (
            PARTITION BY ticker ORDER BY trading_date
        )) / NULLIF(LAG(close_price, 1) OVER (
            PARTITION BY ticker ORDER BY trading_date
        ), 0) * 100, 2
    ) AS calc_daily_return_pct
FROM daily_price_history
WHERE ticker = 'RELIANCE.NS'
ORDER BY trading_date DESC
LIMIT 15;


-- ============================================================================
-- 6. TIMESCALEDB TIME-SERIES HYPERTABLE QUERY
-- ============================================================================

-- 6.1 Weekly Candlestick OHLC Aggregation Using time_bucket
-- Executed on TimescaleDB (daily_price_history hypertable)
-- Note: In standard PostgreSQL, date_trunc('week', trading_date) is used.
SELECT 
    date_trunc('week', trading_date) AS weekly_bucket,
    ticker,
    (ARRAY_AGG(open_price ORDER BY trading_date ASC))[1] AS week_open,
    MAX(high_price) AS week_high,
    MIN(low_price) AS week_low,
    (ARRAY_AGG(close_price ORDER BY trading_date DESC))[1] AS week_close,
    SUM(volume) AS total_weekly_volume
FROM daily_price_history
WHERE ticker = 'TCS.NS'
  AND trading_date >= '2025-01-01'
GROUP BY weekly_bucket, ticker
ORDER BY weekly_bucket DESC;

