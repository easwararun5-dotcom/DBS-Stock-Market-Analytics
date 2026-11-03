-- ============================================================================
-- 08_sector_analysis.sql
-- Description: Sector-wise breakdown, market capitalization weighting, and industry valuation metrics
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 8.1: Sector Weighting and Market Cap Concentration in Nifty 50
-- Demonstrates: Ratio calculation over total index market cap, running cumulative share
-- Business Purpose: Measure sector dominance and index concentration across the 13 sectors.
WITH SectorCaps AS (
    SELECT 
        s.sector_name,
        COUNT(c.ticker) AS company_count,
        SUM(f.market_cap) AS sector_mkt_cap
    FROM sector s
    INNER JOIN company c ON s.sector_id = c.sector_id
    INNER JOIN current_fundamentals f ON c.ticker = f.ticker
    GROUP BY s.sector_name
),
TotalMarket AS (
    SELECT SUM(sector_mkt_cap) AS total_mkt_cap FROM SectorCaps
)
SELECT 
    sc.sector_name,
    sc.company_count,
    ROUND(sc.sector_mkt_cap / 1e12, 2) AS sector_mkt_cap_trillion_inr,
    ROUND((sc.sector_mkt_cap / tm.total_mkt_cap) * 100, 2) AS index_weight_pct,
    ROUND(
        SUM((sc.sector_mkt_cap / tm.total_mkt_cap) * 100) OVER (ORDER BY sc.sector_mkt_cap DESC),
        2
    ) AS cumulative_weight_pct
FROM SectorCaps sc
CROSS JOIN TotalMarket tm
ORDER BY sc.sector_mkt_cap DESC;

-- Query 8.2: Valuation Dispersion within Sectors (P/E Spread)
-- Demonstrates: Calculating valuation dispersion (MAX P/E - MIN P/E) for sectors with multiple constituents
-- Business Purpose: Identify sectors with wide valuation divergences between premium and value names.
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS company_count,
    ROUND(MIN(f.pe_ratio), 2) AS lowest_pe,
    ROUND(MAX(f.pe_ratio), 2) AS highest_pe,
    ROUND(MAX(f.pe_ratio) - MIN(f.pe_ratio), 2) AS pe_spread,
    ROUND(AVG(f.pe_ratio), 2) AS avg_pe
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
WHERE f.pe_ratio IS NOT NULL
GROUP BY s.sector_name
HAVING COUNT(c.ticker) >= 3
ORDER BY pe_spread DESC;

-- Query 8.3: Primary Flagship Company for Each Sector (DISTINCT ON)
-- Demonstrates: PostgreSQL DISTINCT ON (expression) to pick the largest firm per sector
-- Business Purpose: Pinpoint the definitive market leader representing each industry sector.
SELECT DISTINCT ON (s.sector_name)
    s.sector_name,
    c.ticker AS flagship_ticker,
    c.company_name AS flagship_company,
    ROUND(f.market_cap / 1e12, 2) AS market_cap_trillion_inr,
    f.pe_ratio,
    f.dividend_yield
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
ORDER BY s.sector_name, f.market_cap DESC;

-- Query 8.4: Sector Capital Return Profile (Dividends Paid vs Market Cap)
-- Demonstrates: Aggregating historical cash returned through dividends relative to current market cap
-- Business Purpose: Measure long-term cash generation and dividend sustainability across sectors.
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS companies,
    ROUND(SUM(sumry.total_dividends_paid), 2) AS total_dividends_sum,
    ROUND(AVG(sumry.total_dividends_paid), 2) AS avg_dividends_per_company,
    ROUND(AVG(f.dividend_yield), 2) AS avg_current_dividend_yield,
    ROUND(SUM(f.market_cap) / 1e12, 2) AS sector_market_cap_trillion
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN stock_summary sumry ON c.ticker = sumry.ticker
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
GROUP BY s.sector_name
ORDER BY total_dividends_sum DESC;

-- Query 8.5: Sector Risk & Volatility Profile (Beta & Volatility Averages)
-- Demonstrates: Multi-variable risk ranking using fundamental beta and realized price volatility
-- Business Purpose: Classify sectors into high-beta (cyclical) vs low-beta (defensive) groups.
SELECT 
    s.sector_name,
    COUNT(c.ticker) AS company_count,
    ROUND(AVG(f.beta), 2) AS avg_sector_beta,
    ROUND(MIN(f.beta), 2) AS min_beta,
    ROUND(MAX(f.beta), 2) AS max_beta,
    ROUND(AVG(sumry.volatility_pct), 2) AS avg_realized_volatility,
    CASE 
        WHEN AVG(f.beta) > 1.10 THEN 'High Beta (Aggressive)'
        WHEN AVG(f.beta) BETWEEN 0.85 AND 1.10 THEN 'Market Beta (Neutral)'
        ELSE 'Low Beta (Defensive)'
    END AS risk_classification
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker
INNER JOIN stock_summary sumry ON c.ticker = sumry.ticker
WHERE f.beta IS NOT NULL
GROUP BY s.sector_name
ORDER BY avg_sector_beta DESC;
