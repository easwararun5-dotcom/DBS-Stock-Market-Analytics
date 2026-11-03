-- ============================================================================
-- 04_subqueries.sql
-- Description: Nested subqueries (Scalar, IN/NOT IN, Subqueries in FROM/SELECT)
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 4.1: Companies with P/E Below Overall Market Average (Scalar Subquery in WHERE)
-- Demonstrates: Filtering against a scalar aggregate subquery
-- Business Purpose: Identify stocks trading at a valuation discount relative to the Nifty 50 average.
SELECT 
    ticker,
    pe_ratio,
    forward_pe,
    price_to_book,
    dividend_yield
FROM current_fundamentals
WHERE pe_ratio IS NOT NULL 
  AND pe_ratio < (
      SELECT AVG(pe_ratio) 
      FROM current_fundamentals 
      WHERE pe_ratio IS NOT NULL
  )
ORDER BY pe_ratio ASC;

-- Query 4.2: Companies with Market Cap Above the Market Median (PERCENTILE_CONT Subquery)
-- Demonstrates: Scalar subquery using continuous percentile function in WHERE
-- Business Purpose: Isolate upper-half large-cap leaders using robust median metric.
SELECT 
    f.ticker,
    c.company_name,
    f.market_cap,
    ROUND(f.market_cap / 1e12, 2) AS market_cap_trillion_inr
FROM current_fundamentals f
INNER JOIN company c ON f.ticker = c.ticker
WHERE f.market_cap >= (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY market_cap)
    FROM current_fundamentals
)
ORDER BY f.market_cap DESC;

-- Query 4.3: Stocks Belonging to the Top 3 Largest Industry Sectors (Subquery with IN)
-- Demonstrates: Set-membership subquery (WHERE column IN (SELECT ...))
-- Business Purpose: Filter companies belonging exclusively to the dominant macroeconomic sectors.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.market_cap
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
WHERE s.sector_id IN (
    SELECT sector_id
    FROM (
        SELECT 
            comp.sector_id,
            SUM(fund.market_cap) AS sector_mktcap
        FROM company comp
        INNER JOIN current_fundamentals fund ON comp.ticker = fund.ticker
        GROUP BY comp.sector_id
        ORDER BY sector_mktcap DESC
        LIMIT 3
    ) top_sectors
)
ORDER BY s.sector_name, f.market_cap DESC;

-- Query 4.4: Derived Table Comparing Year 2025 Volume against Lifetime Average (Subquery in FROM)
-- Demonstrates: Derived table with aggregated metrics joined with base company dimension
-- Business Purpose: Detect stocks experiencing unusual trading surge or institutional interest in recent years.
SELECT 
    v2025.ticker,
    c.company_name,
    v2025.avg_vol_2025,
    sumry.avg_daily_volume AS lifetime_avg_vol,
    ROUND((v2025.avg_vol_2025 - sumry.avg_daily_volume) / sumry.avg_daily_volume * 100, 2) AS volume_change_pct
FROM (
    SELECT 
        ticker,
        ROUND(AVG(volume), 2) AS avg_vol_2025
    FROM daily_price_history
    WHERE trading_date BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY ticker
) v2025
INNER JOIN company c ON v2025.ticker = c.ticker
INNER JOIN stock_summary sumry ON v2025.ticker = sumry.ticker
WHERE sumry.avg_daily_volume > 0
ORDER BY volume_change_pct DESC
LIMIT 15;

-- Query 4.5: Market Leaders by Sector (Subquery in SELECT)
-- Demonstrates: Scalar subquery in SELECT clause calculating market cap share of sector
-- Business Purpose: Measure single-company concentration within its respective industry sector.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.market_cap,
    ROUND(
        f.market_cap * 100.0 / (
            SELECT SUM(fund2.market_cap)
            FROM company comp2
            INNER JOIN current_fundamentals fund2 ON comp2.ticker = fund2.ticker
            WHERE comp2.sector_id = c.sector_id
        ),
        2
    ) AS sector_market_cap_share_pct
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY sector_market_cap_share_pct DESC
LIMIT 15;
