-- ============================================================================
-- 03_aggregations_group_by.sql
-- Description: Aggregate functions (COUNT, SUM, AVG, MIN, MAX) with GROUP BY and HAVING
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 3.1: Sector-Level Market Capitalization and Valuation Aggregates
-- Demonstrates: COUNT, SUM, AVG, MIN, MAX, GROUP BY
-- Business Purpose: Compare sector scale and average valuation multiples across all 13 industries.
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS company_count,
    ROUND(SUM(f.market_cap) / 1e12, 2) AS total_market_cap_trillion_inr,
    ROUND(AVG(f.pe_ratio), 2) AS avg_pe_ratio,
    ROUND(MIN(f.pe_ratio), 2) AS min_pe_ratio,
    ROUND(MAX(f.pe_ratio), 2) AS max_pe_ratio,
    ROUND(AVG(f.dividend_yield), 2) AS avg_dividend_yield
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
GROUP BY s.sector_name
ORDER BY total_market_cap_trillion_inr DESC;

-- Query 3.2: Sectors with High Corporate Action Activity (HAVING filter)
-- Demonstrates: COUNT, SUM with conditional CASE, GROUP BY, HAVING count > threshold
-- Business Purpose: Identify sectors whose constituent companies frequently return capital or split stock.
SELECT 
    s.sector_name,
    COUNT(DISTINCT c.ticker) AS active_companies,
    COUNT(a.action_id) AS total_corporate_actions,
    COUNT(CASE WHEN a.action_type = 'Dividend' THEN 1 END) AS total_dividends,
    COUNT(CASE WHEN a.action_type = 'Stock_Split' THEN 1 END) AS total_splits
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN corporate_action a ON c.ticker = a.ticker
GROUP BY s.sector_name
HAVING COUNT(a.action_id) >= 100
ORDER BY total_corporate_actions DESC;

-- Query 3.3: Annual Trading Volume and Return Profile for TCS (Yearly Aggregation)
-- Demonstrates: EXTRACT(YEAR FROM date), AVG, MIN, MAX, SUM, GROUP BY year
-- Business Purpose: Analyze year-over-year trading activity, price range expansion, and average volume for TCS.
SELECT 
    EXTRACT(YEAR FROM p.trading_date)::INT AS trading_year,
    COUNT(*) AS trading_days,
    ROUND(AVG(p.close_price), 2) AS avg_close_price,
    ROUND(MIN(p.low_price), 2) AS min_low_price,
    ROUND(MAX(p.high_price), 2) AS max_high_price,
    ROUND(AVG(p.volume) / 1e6, 2) AS avg_daily_vol_million,
    ROUND(AVG(p.daily_return) * 100, 3) AS avg_daily_return_pct
FROM daily_price_history p
WHERE p.ticker = 'TCS.NS'
GROUP BY EXTRACT(YEAR FROM p.trading_date)
ORDER BY trading_year DESC;

-- Query 3.4: Return Performance Grouped by Number of Stock Splits
-- Demonstrates: Grouping by discrete split count, AVG, MIN, MAX with HAVING filter
-- Business Purpose: Test whether companies with higher split frequency correlate with higher historical total returns.
SELECT 
    sumry.number_of_splits,
    COUNT(*) AS company_count,
    ROUND(AVG(sumry.total_return_pct), 2) AS avg_total_return_pct,
    ROUND(MIN(sumry.total_return_pct), 2) AS min_total_return_pct,
    ROUND(MAX(sumry.total_return_pct), 2) AS max_total_return_pct,
    ROUND(AVG(sumry.avg_daily_volume) / 1e6, 2) AS avg_daily_vol_million
FROM stock_summary sumry
WHERE sumry.total_return_pct > 0 -- Exclude negative return artifact from backwards dividend subtraction
GROUP BY sumry.number_of_splits
HAVING COUNT(*) >= 2
ORDER BY sumry.number_of_splits DESC;

-- Query 3.5: Industry Sectors with Outstanding Average Returns (HAVING on AVG)
-- Demonstrates: Aggregate filter on calculated mean percentage return
-- Business Purpose: Identify the top-performing macroeconomic sectors over the 25-year sample period.
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS company_count,
    ROUND(AVG(sumry.total_return_pct), 2) AS avg_total_return_pct,
    ROUND(AVG(sumry.volatility_pct), 2) AS avg_volatility_pct
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN stock_summary sumry ON c.ticker = sumry.ticker
WHERE sumry.total_return_pct > 0
GROUP BY s.sector_name
HAVING AVG(sumry.total_return_pct) >= 20000.0
ORDER BY avg_total_return_pct DESC;
