-- ============================================================================
-- View 6: v_corporate_action_summary
-- Description: Company-wise corporate action summary (dividends and stock splits)
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Purpose:
-- Provides an aggregated corporate-action profile per company, including the number
-- of dividend events, cumulative dividend paid, the first and last dividend dates,
-- the number of stock splits, and the first and last split dates.
-- Tickers with no recorded actions are excluded (INNER JOIN with corporate_action).

-- Underlying SQL Concepts:
-- 1. GROUP BY aggregation on ticker with FILTER to separate dividend from split rows.
-- 2. MIN/MAX on dates to surface the timeline of events.
-- 3. EXP(SUM(LN(value))) idiom for geometric product (cumulative split factor).
--    Cast to double precision because LN requires a float argument.

CREATE OR REPLACE VIEW v_corporate_action_summary AS
SELECT
    c.ticker,
    c.company_name,
    s.sector_name,

    -- Dividend metrics
    COUNT(*)              FILTER (WHERE ca.action_type = 'Dividend')      AS dividend_event_count,
    COALESCE(
        SUM(ca.action_value) FILTER (WHERE ca.action_type = 'Dividend'),
        0
    )                                                                      AS total_dividends_paid,
    MIN(ca.action_date)   FILTER (WHERE ca.action_type = 'Dividend')      AS first_dividend_date,
    MAX(ca.action_date)   FILTER (WHERE ca.action_type = 'Dividend')      AS last_dividend_date,
    ROUND(
        COALESCE(
            AVG(ca.action_value) FILTER (WHERE ca.action_type = 'Dividend'),
            0
        ), 4
    )                                                                      AS avg_dividend_per_event,

    -- Stock-split metrics
    COUNT(*)              FILTER (WHERE ca.action_type = 'Stock_Split')   AS split_event_count,
    MIN(ca.action_date)   FILTER (WHERE ca.action_type = 'Stock_Split')   AS first_split_date,
    MAX(ca.action_date)   FILTER (WHERE ca.action_type = 'Stock_Split')   AS last_split_date,
    -- Cumulative split factor: product of all split ratios using exp(sum(ln(x)))
    COALESCE(
        EXP(
            SUM(LN(ca.action_value::double precision))
                FILTER (WHERE ca.action_type = 'Stock_Split')
        ),
        1.0
    )                                                                      AS cumulative_split_factor

FROM corporate_action ca
JOIN company c ON c.ticker = ca.ticker
JOIN sector s ON s.sector_id = c.sector_id
GROUP BY c.ticker, c.company_name, s.sector_name
ORDER BY total_dividends_paid DESC;

COMMENT ON VIEW v_corporate_action_summary IS 'Company-wise summary of dividend events, cumulative dividends paid, split counts, and cumulative split factor.';
