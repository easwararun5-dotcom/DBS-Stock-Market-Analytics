-- ============================================================================
-- 10_corporate_actions.sql
-- Description: Dividend distribution history, stock split frequency, and cumulative split multipliers
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 10.1: Top Dividend Aristocrats by Lifetime Payments
-- Demonstrates: Aggregating child action records with count, sum, average, min, and max payout per event
-- Business Purpose: Identify consistent cash-generating dividend payers in the Nifty 50.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    COUNT(a.action_id) AS total_dividend_payments,
    ROUND(SUM(a.action_value), 2) AS total_dividends_paid_inr,
    ROUND(AVG(a.action_value), 2) AS avg_payout_per_event_inr,
    ROUND(MIN(a.action_value), 2) AS min_payout_inr,
    ROUND(MAX(a.action_value), 2) AS max_payout_inr,
    MIN(a.action_date) AS first_dividend_date,
    MAX(a.action_date) AS latest_dividend_date
FROM corporate_action a
INNER JOIN company c ON a.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE a.action_type = 'Dividend'
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY total_dividend_payments DESC
LIMIT 15;

-- Query 10.2: Annual Dividend Growth Trajectory for IT & FMCG Giants
-- Demonstrates: Grouping by EXTRACT(YEAR FROM action_date) with conditional column sums
-- Business Purpose: Track yearly dividend cash distributions for TCS, Infosys, and ITC over time.
SELECT 
    EXTRACT(YEAR FROM a.action_date)::INT AS payout_year,
    ROUND(SUM(CASE WHEN a.ticker = 'TCS.NS' THEN a.action_value ELSE 0 END), 2) AS tcs_dividend_inr,
    ROUND(SUM(CASE WHEN a.ticker = 'INFY.NS' THEN a.action_value ELSE 0 END), 2) AS infy_dividend_inr,
    ROUND(SUM(CASE WHEN a.ticker = 'ITC.NS' THEN a.action_value ELSE 0 END), 2) AS itc_dividend_inr
FROM corporate_action a
WHERE a.ticker IN ('TCS.NS', 'INFY.NS', 'ITC.NS')
  AND a.action_type = 'Dividend'
GROUP BY EXTRACT(YEAR FROM a.action_date)
ORDER BY payout_year DESC
LIMIT 15;

-- Query 10.3: Cumulative Share Multiplier from Stock Splits
-- Demonstrates: Logarithmic sum exponentiation EXP(SUM(LN(action_value))) to compute cumulative product
-- Business Purpose: Quantify how many shares an investor would own today from 1 original IPO/base share.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    COUNT(a.action_id) AS total_splits,
    ROUND(EXP(SUM(LN(a.action_value)))::numeric, 1) AS cumulative_share_multiplier,
    MIN(a.action_date) AS first_split_date,
    MAX(a.action_date) AS latest_split_date
FROM corporate_action a
INNER JOIN company c ON a.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE a.action_type = 'Stock_Split'
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY cumulative_share_multiplier DESC
LIMIT 15;

-- Query 10.4: Simultaneous Corporate Action Events (Dual Dividend and Split on Same Date)
-- Demonstrates: Self-join on corporate_action to identify days when both dividend and split coincided
-- Business Purpose: Inspect the exact historical dates when corporate boards combined cash payouts with share splits.
SELECT 
    d.ticker,
    c.company_name,
    d.action_date,
    d.action_value AS dividend_amount_inr,
    s.action_value AS split_ratio
FROM corporate_action d
INNER JOIN corporate_action s 
    ON d.ticker = s.ticker 
   AND d.action_date = s.action_date 
   AND s.action_type = 'Stock_Split'
INNER JOIN company c ON d.ticker = c.ticker
WHERE d.action_type = 'Dividend'
ORDER BY d.action_date DESC;

-- Query 10.5: Corporate Action Frequency by Sector
-- Demonstrates: Sector-level breakdown of dividends vs stock splits and average cash paid per sector
-- Business Purpose: Analyze how different industries prefer to reward shareholders (cash dividends vs stock splits).
SELECT 
    s.sector_name,
    COUNT(DISTINCT c.ticker) AS companies_in_sector,
    COUNT(CASE WHEN a.action_type = 'Dividend' THEN 1 END) AS total_dividends_declared,
    COUNT(CASE WHEN a.action_type = 'Stock_Split' THEN 1 END) AS total_splits_executed,
    ROUND(SUM(CASE WHEN a.action_type = 'Dividend' THEN a.action_value ELSE 0 END), 2) AS sector_total_dividends_inr,
    ROUND(
        SUM(CASE WHEN a.action_type = 'Dividend' THEN a.action_value ELSE 0 END) / 
        NULLIF(COUNT(DISTINCT c.ticker), 0), 
        2
    ) AS avg_dividends_per_company_inr
FROM sector s
INNER JOIN company c ON s.sector_id = c.sector_id
LEFT JOIN corporate_action a ON c.ticker = a.ticker
GROUP BY s.sector_name
ORDER BY total_dividends_declared DESC;
