-- ============================================================================
-- View 4: v_sector_performance
-- Description: Sector-wise market capitalisation and performance aggregates
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Provides sector-level rollups of market cap, company count, valuation ratios,
-- dividend yield, total returns, and volatility. NULLs are excluded from AVG
-- calculations via the FILTER clause so they do not distort averages.

-- Underlying SQL Concepts:
-- 1. GROUP BY aggregation on sector.
-- 2. FILTER (WHERE ...) to exclude NULLs from AVG without removing rows.
-- 3. ROUND() for display precision.

CREATE OR REPLACE VIEW v_sector_performance AS
SELECT
    s.sector_id,
    s.sector_name,
    COUNT(DISTINCT c.ticker)                                                    AS num_companies,
    ROUND(SUM(f.market_cap) / 1e12, 2)                                         AS total_market_cap_trillion_inr,
    ROUND(AVG(f.pe_ratio)         FILTER (WHERE f.pe_ratio IS NOT NULL), 2)    AS avg_pe_ratio,
    ROUND(AVG(f.forward_pe)       FILTER (WHERE f.forward_pe IS NOT NULL), 2)  AS avg_forward_pe,
    ROUND(AVG(f.price_to_book)    FILTER (WHERE f.price_to_book IS NOT NULL), 2) AS avg_price_to_book,
    ROUND(AVG(f.dividend_yield)   FILTER (WHERE f.dividend_yield IS NOT NULL), 4) AS avg_dividend_yield,
    ROUND(AVG(f.beta)             FILTER (WHERE f.beta IS NOT NULL), 4)        AS avg_beta,
    ROUND(AVG(ss.total_return_pct)    FILTER (WHERE ss.total_return_pct IS NOT NULL), 2) AS avg_total_return_pct,
    ROUND(AVG(ss.volatility_pct)      FILTER (WHERE ss.volatility_pct IS NOT NULL), 4) AS avg_volatility_pct,
    ROUND(AVG(ss.avg_daily_return_pct) FILTER (WHERE ss.avg_daily_return_pct IS NOT NULL), 6) AS avg_daily_return_pct,
    SUM(ss.total_dividends_paid)                                                AS sector_total_dividends
FROM sector s
JOIN company c ON c.sector_id = s.sector_id
JOIN current_fundamentals f ON f.ticker = c.ticker
JOIN stock_summary ss ON ss.ticker = c.ticker
GROUP BY s.sector_id, s.sector_name
ORDER BY total_market_cap_trillion_inr DESC NULLS LAST;

COMMENT ON VIEW v_sector_performance IS 'Sector-level market cap, valuation ratios, and performance aggregates.';
