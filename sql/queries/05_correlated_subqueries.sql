-- ============================================================================
-- 05_correlated_subqueries.sql
-- Description: Correlated subqueries (WHERE, SELECT, and EXISTS)
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 5.1: Companies Trading at a Discount to Their Own Sector Average P/E (Correlated WHERE)
-- Demonstrates: Correlated subquery where inner query references outer query's c.sector_id
-- Business Purpose: Identify intra-sector value bargains by comparing stocks directly against industry peers.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.pe_ratio,
    ROUND((
        SELECT AVG(f2.pe_ratio)
        FROM company c2
        INNER JOIN current_fundamentals f2 ON c2.ticker = f2.ticker
        WHERE c2.sector_id = c.sector_id AND f2.pe_ratio IS NOT NULL
    ), 2) AS sector_avg_pe,
    ROUND(
        f.pe_ratio - (
            SELECT AVG(f2.pe_ratio)
            FROM company c2
            INNER JOIN current_fundamentals f2 ON c2.ticker = f2.ticker
            WHERE c2.sector_id = c.sector_id AND f2.pe_ratio IS NOT NULL
        ), 
        2
    ) AS pe_discount_to_sector
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
WHERE f.pe_ratio IS NOT NULL
  AND f.pe_ratio < (
      SELECT AVG(f2.pe_ratio)
      FROM company c2
      INNER JOIN current_fundamentals f2 ON c2.ticker = f2.ticker
      WHERE c2.sector_id = c.sector_id AND f2.pe_ratio IS NOT NULL
  )
ORDER BY pe_discount_to_sector ASC;

-- Query 5.2: Companies Outperforming Their Sector Average Total Return (Correlated WHERE)
-- Demonstrates: Correlated subquery filtering based on intra-sector mean performance
-- Business Purpose: Find alpha-generating stocks that beat their specific industry benchmark return.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    sumry.total_return_pct,
    ROUND((
        SELECT AVG(sumry2.total_return_pct)
        FROM company c2
        INNER JOIN stock_summary sumry2 ON c2.ticker = sumry2.ticker
        WHERE c2.sector_id = c.sector_id AND sumry2.total_return_pct > 0
    ), 2) AS sector_avg_return_pct
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN stock_summary sumry ON c.ticker = sumry.ticker
WHERE sumry.total_return_pct > 0
  AND sumry.total_return_pct > (
      SELECT AVG(sumry2.total_return_pct)
      FROM company c2
      INNER JOIN stock_summary sumry2 ON c2.ticker = sumry2.ticker
      WHERE c2.sector_id = c.sector_id AND sumry2.total_return_pct > 0
  )
ORDER BY sumry.total_return_pct DESC;

-- Query 5.3: Companies That Have Executed Mega Stock Splits (Correlated EXISTS)
-- Demonstrates: Correlated EXISTS clause checking child table existence
-- Business Purpose: Isolate companies that underwent major capital restructurings (split ratio >= 5.0, e.g. 5:1 or 10:1).
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE EXISTS (
    SELECT 1 
    FROM corporate_action a
    WHERE a.ticker = c.ticker 
      AND a.action_type = 'Stock_Split' 
      AND a.action_value >= 5.0
)
ORDER BY c.ticker;

-- Query 5.4: Each Company's Single Highest Daily Volume Spike and Its Date (Correlated Scalar)
-- Demonstrates: Correlated subqueries matching max value and date of maximum event
-- Business Purpose: Locate historical capitulation or breakout volume peaks for institutional analysis.
SELECT 
    c.ticker,
    c.company_name,
    p.trading_date AS peak_volume_date,
    p.volume AS peak_daily_volume,
    p.close_price AS price_at_peak
FROM company c
INNER JOIN daily_price_history p ON c.ticker = p.ticker
WHERE p.volume = (
    SELECT MAX(p2.volume)
    FROM daily_price_history p2
    WHERE p2.ticker = c.ticker
)
ORDER BY p.volume DESC
LIMIT 15;

-- Query 5.5: Distance from 52-Week High per Company (Correlated Subquery in SELECT)
-- Demonstrates: Correlated subquery computing rolling 1-year high from historical price table
-- Business Purpose: Measure percentage pullback from 52-week peak for momentum and drawdown screening.
SELECT 
    c.ticker,
    c.company_name,
    f.last_updated AS current_date,
    latest_p.close_price AS latest_close,
    (
        SELECT MAX(p_year.high_price)
        FROM daily_price_history p_year
        WHERE p_year.ticker = c.ticker
          AND p_year.trading_date >= '2025-01-30'
    ) AS high_52_week,
    ROUND(
        (latest_p.close_price - (
            SELECT MAX(p_year.high_price)
            FROM daily_price_history p_year
            WHERE p_year.ticker = c.ticker
              AND p_year.trading_date >= '2025-01-30'
        )) * 100.0 / (
            SELECT MAX(p_year.high_price)
            FROM daily_price_history p_year
            WHERE p_year.ticker = c.ticker
              AND p_year.trading_date >= '2025-01-30'
        ),
        2
    ) AS drawdown_from_52w_high_pct
FROM company c
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
INNER JOIN daily_price_history latest_p 
    ON c.ticker = latest_p.ticker 
   AND latest_p.trading_date = f.last_updated
ORDER BY drawdown_from_52w_high_pct ASC
LIMIT 15;
