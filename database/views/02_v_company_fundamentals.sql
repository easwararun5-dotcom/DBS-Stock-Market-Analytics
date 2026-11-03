-- ============================================================================
-- View 2: v_company_fundamentals
-- Description: Company details combined with sector information and fundamental ratios
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Provides a clean equity valuation view joining company master data,
-- sector classifications, and fundamental financial metrics.
-- Includes derived scale metrics and categorizations while handling NULL values.

-- Underlying SQL Concepts:
-- 1. Multi-table INNER JOIN across sector, company, and current_fundamentals.
-- 2. NULL-safe handling and analytical categorization using CASE expressions.
-- 3. Documented source-data limitations (e.g. peg_ratio is 100% NULL in source dataset;
--    fiscal_year is a derived snapshot year, not an officially verified company fiscal year).

CREATE OR REPLACE VIEW v_company_fundamentals AS
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.market_cap,
    ROUND(f.market_cap / 1e12, 2) AS market_cap_trillion_inr,
    ROUND(f.market_cap / 1e9, 2) AS market_cap_billion_inr,
    f.pe_ratio,
    f.forward_pe,
    f.price_to_book,
    f.dividend_yield,
    f.eps,
    f.beta,
    f.fiscal_year,  -- Note: Derived snapshot year (2026) from latest available date
    f.peg_ratio,    -- Note: 100% NULL across source dataset
    CASE 
        WHEN f.pe_ratio IS NULL THEN 'N/A (Missing)'
        WHEN f.pe_ratio < 15.0 THEN 'Deep Value (P/E < 15)'
        WHEN f.pe_ratio BETWEEN 15.0 AND 30.0 THEN 'Moderate Valuation (P/E 15-30)'
        WHEN f.pe_ratio BETWEEN 30.0 AND 50.0 THEN 'Growth / Premium (P/E 30-50)'
        ELSE 'High Multiple (P/E > 50)'
    END AS valuation_tier,
    CASE 
        WHEN f.dividend_yield IS NULL THEN 'N/A'
        WHEN f.dividend_yield >= 3.0 THEN 'High Dividend (> 3%)'
        WHEN f.dividend_yield BETWEEN 1.0 AND 3.0 THEN 'Moderate Dividend (1-3%)'
        ELSE 'Low / No Dividend (< 1%)'
    END AS dividend_tier,
    f.last_updated
FROM company c
INNER JOIN sector s ON c.sector_id = s.sector_id
INNER JOIN current_fundamentals f ON c.ticker = f.ticker;

COMMENT ON VIEW v_company_fundamentals IS 'Company profile with sector classification, fundamental valuation multiples, and dividend tiers.';
