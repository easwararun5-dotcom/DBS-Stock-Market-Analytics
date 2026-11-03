-- ============================================================================
-- 06_window_functions.sql
-- Description: Window functions (RANK, DENSE_RANK, ROW_NUMBER, LAG, and running calculations)
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 6.1: Sector-Wise Company Ranking by Market Capitalization
-- Demonstrates: RANK() and DENSE_RANK() with PARTITION BY sector_name ORDER BY market_cap DESC
-- Business Purpose: Identify the rank and competitive standing of each firm within its industry group.
SELECT 
    s.sector_name,
    c.ticker,
    c.company_name,
    ROUND(f.market_cap / 1e12, 2) AS market_cap_trillion_inr,
    RANK() OVER (PARTITION BY s.sector_name ORDER BY f.market_cap DESC) AS sector_rank,
    DENSE_RANK() OVER (PARTITION BY s.sector_name ORDER BY f.market_cap DESC) AS sector_dense_rank
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY s.sector_name, sector_rank;

-- Query 6.2: Top 3 Highest-Volume Trading Sessions per IT Stock
-- Demonstrates: ROW_NUMBER() with PARTITION BY ticker ORDER BY volume DESC, filtered in outer CTE
-- Business Purpose: Isolate the three most intense trading days for major technology equities.
WITH RankedVolume AS (
    SELECT 
        c.ticker,
        c.company_name,
        p.trading_date,
        p.volume,
        p.close_price,
        p.daily_return,
        ROW_NUMBER() OVER (PARTITION BY c.ticker ORDER BY p.volume DESC) AS vol_rank
    FROM company c
    INNER JOIN sector s ON c.sector_id = s.sector_id
    INNER JOIN daily_price_history p ON c.ticker = p.ticker
    WHERE s.sector_name = 'IT'
)
SELECT 
    ticker,
    company_name,
    trading_date,
    volume,
    close_price,
    ROUND(daily_return * 100, 2) AS daily_return_pct,
    vol_rank
FROM RankedVolume
WHERE vol_rank <= 3
ORDER BY ticker, vol_rank;

-- Query 6.3: Running 7-Day Moving Average and Cumulative Volume for RELIANCE.NS
-- Demonstrates: Window frame (ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), running SUM OVER
-- Business Purpose: Smooth price action over short-term windows and track cumulative volume execution.
SELECT 
    p.ticker,
    p.trading_date,
    p.close_price,
    ROUND(AVG(p.close_price) OVER (
        PARTITION BY p.ticker 
        ORDER BY p.trading_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS moving_avg_7d,
    p.volume,
    SUM(p.volume) OVER (
        PARTITION BY p.ticker 
        ORDER BY p.trading_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_volume
FROM daily_price_history p
WHERE p.ticker = 'RELIANCE.NS'
  AND p.trading_date >= '2026-01-01'
ORDER BY p.trading_date ASC;

-- Query 6.4: Calculating Price Returns with LAG() and Lead/Lag Comparisons
-- Demonstrates: LAG(column, 1) OVER (PARTITION BY ... ORDER BY ...), comparing computed return with precomputed column
-- Business Purpose: Verify historical return computation formula against dataset technical indicator.
SELECT 
    p.ticker,
    p.trading_date,
    p.close_price,
    LAG(p.close_price, 1) OVER (PARTITION BY p.ticker ORDER BY p.trading_date) AS prev_close_price,
    ROUND(
        (p.close_price - LAG(p.close_price, 1) OVER (PARTITION BY p.ticker ORDER BY p.trading_date)) / 
        LAG(p.close_price, 1) OVER (PARTITION BY p.ticker ORDER BY p.trading_date),
        4
    ) AS computed_daily_return,
    p.daily_return AS dataset_daily_return
FROM daily_price_history p
WHERE p.ticker = 'TCS.NS'
  AND p.trading_date >= '2026-01-10'
ORDER BY p.trading_date ASC;

-- Query 6.5: Stock Quartiles and Percentile Ranking by Lifetime Return
-- Demonstrates: NTILE(4) to divide stocks into 4 quartiles, PERCENT_RANK() for relative percentile
-- Business Purpose: Segment the stock universe into performance quartiles for asset allocation.
SELECT 
    sumry.ticker,
    c.company_name,
    s.sector_name,
    sumry.total_return_pct,
    NTILE(4) OVER (ORDER BY sumry.total_return_pct DESC) AS return_quartile,
    ROUND(PERCENT_RANK() OVER (ORDER BY sumry.total_return_pct ASC)::numeric, 4) AS return_percentile
FROM stock_summary sumry
INNER JOIN company c ON sumry.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE sumry.total_return_pct > 0
ORDER BY sumry.total_return_pct DESC
LIMIT 15;
