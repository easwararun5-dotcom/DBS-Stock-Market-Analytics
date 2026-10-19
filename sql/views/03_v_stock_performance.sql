-- ============================================================================
-- View 3: v_stock_performance
-- Description: Company performance metrics combining fundamentals, market cap, and summary statistics
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Provides a comprehensive performance snapshot per ticker, including market cap, P/E,
-- valuation tier, and key summary statistics such as total return, average daily return,
-- and volatility. NULL values are preserved where source data is missing.

-- Underlying SQL Concepts:
-- 1. INNER JOIN across sector, company, current_fundamentals, and stock_summary.
-- 2. CASE expressions for valuation tier categorization (reused from fundamentals view).
-- 3. Handling of NULLs without coercion.

CREATE OR REPLACE VIEW v_stock_performance AS
SELECT
    c.ticker,
    c.company_name,
    s.sector_name,
    f.market_cap,
    f.pe_ratio,
    f.forward_pe,
    f.price_to_book,
    f.dividend_yield,
    f.eps,
    f.beta,
    f.fiscal_year,
    CASE
        WHEN f.pe_ratio IS NULL THEN 'N/A (Missing)'
        WHEN f.pe_ratio < 15.0 THEN 'Deep Value (P/E < 15)'
        WHEN f.pe_ratio BETWEEN 15.0 AND 30.0 THEN 'Moderate Valuation (P/E 15-30)'
        WHEN f.pe_ratio BETWEEN 30.0 AND 50.0 THEN 'Growth / Premium (P/E 30-50)'
        ELSE 'High Multiple (P/E > 50)'
    END AS valuation_tier,
    ss.total_trading_days,
    ss.total_return_pct,
    ss.avg_daily_return_pct,
    ss.volatility_pct,
    ss.highest_price,
    ss.lowest_price,
    ss.total_dividends_paid,
    ss.number_of_splits,
    f.last_updated
FROM company c
JOIN sector s ON c.sector_id = s.sector_id
JOIN current_fundamentals f ON c.ticker = f.ticker
JOIN stock_summary ss ON c.ticker = ss.ticker;

COMMENT ON VIEW v_stock_performance IS 'Performance snapshot per company combining fundamentals and long‑term summary statistics.';
