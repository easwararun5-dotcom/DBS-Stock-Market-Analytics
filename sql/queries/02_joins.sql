-- ============================================================================
-- 02_joins.sql
-- Description: INNER JOIN and LEFT JOIN queries across financial tables
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 2.1: Company Profile with Sector Name (INNER JOIN)
-- Demonstrates: Standard 2-table INNER JOIN on foreign key (company.sector_id = sector.sector_id)
-- Business Purpose: Map stock ticker symbols to human-readable company names and sectors.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
ORDER BY s.sector_name, c.company_name;

-- Query 2.2: Company Fundamentals with Sector Context (Multi-table INNER JOIN)
-- Demonstrates: 3-table INNER JOIN (company, sector, current_fundamentals)
-- Business Purpose: Comprehensive valuation view showing P/E, P/B, EPS, and Market Cap by Sector.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.pe_ratio,
    f.forward_pe,
    f.price_to_book,
    f.eps,
    f.market_cap
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY f.market_cap DESC
LIMIT 15;

-- Query 2.3: Companies and Corporate Action Summary (LEFT JOIN with Aggregation)
-- Demonstrates: LEFT JOIN to include companies even if they have 0 corporate actions, COALESCE
-- Business Purpose: Audit which companies have paid dividends vs those that have never issued corporate actions.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    COUNT(a.action_id) AS total_corporate_actions,
    COUNT(CASE WHEN a.action_type = 'Dividend' THEN 1 END) AS dividend_count,
    COUNT(CASE WHEN a.action_type = 'Stock_Split' THEN 1 END) AS split_count,
    COALESCE(SUM(CASE WHEN a.action_type = 'Dividend' THEN a.action_value END), 0) AS total_dividends_sum
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
LEFT JOIN corporate_action a ON c.ticker = a.ticker
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY total_dividends_sum DESC
LIMIT 15;

-- Query 2.4: Long-term Stock Summary with Sector and Valuation (INNER JOIN)
-- Demonstrates: Joining summary statistics with master company and sector dimensions
-- Business Purpose: Compare total historical return and volatility alongside industry sectors.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    sumry.first_trading_date,
    sumry.last_trading_date,
    sumry.total_trading_days,
    sumry.total_return_pct,
    sumry.avg_daily_volume,
    sumry.current_market_cap
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN stock_summary sumry ON c.ticker = sumry.ticker
ORDER BY sumry.total_return_pct DESC
LIMIT 15;

-- Query 2.5: Price Movement on Corporate Action Ex-Dates (LEFT JOIN)
-- Demonstrates: Joining daily price history with corporate action events on composite (ticker, date)
-- Business Purpose: Analyze daily return and price volatility on days when dividends or stock splits took effect.
SELECT 
    p.ticker,
    p.trading_date,
    p.close_price,
    p.daily_return,
    p.volume,
    a.action_type,
    a.action_value
FROM daily_price_history p
INNER JOIN corporate_action a 
    ON p.ticker = a.ticker 
   AND p.trading_date = a.action_date
WHERE p.ticker IN ('TCS.NS', 'INFY.NS', 'RELIANCE.NS')
ORDER BY p.trading_date DESC
LIMIT 15;
