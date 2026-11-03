-- ============================================================================
-- Function: calculate_portfolio_value(p_user_id INTEGER)
-- Returns:  TABLE – per-holding breakdown plus a total row
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   For each active holding owned by the user (quantity > 0), fetch the latest
--   available closing price from daily_price_history and multiply by the
--   remaining holding quantity.
--
-- Pure 3NF Update:
--   Joins through user_portfolio on portfolio_id to identify holdings owned by p_user_id.
--
-- Business rules:
--   - Reflects active holdings with quantity > 0 (closed positions with 0
--     shares are excluded from portfolio valuation).
--   - If a holding's ticker has no price history, latest_price and market_value
--     are NULL.
--   - Returns zero rows (empty set) when the user has no active holdings.
--   - Does not raise an exception for unknown user IDs; returns empty.
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_portfolio_value(p_user_id INTEGER)
RETURNS TABLE (
    holding_id    INTEGER,
    ticker        TEXT,
    company_name  TEXT,
    quantity      NUMERIC,
    latest_price  NUMERIC,
    market_value  NUMERIC
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT
        ph.holding_id,
        ph.ticker,
        c.company_name,
        ph.quantity,
        lp.close_price                              AS latest_price,
        ph.quantity * lp.close_price                AS market_value
    FROM portfolio_holding ph
    JOIN user_portfolio up ON ph.portfolio_id = up.portfolio_id
    JOIN company c ON c.ticker = ph.ticker
    LEFT JOIN LATERAL (
        SELECT dph.close_price
        FROM daily_price_history dph
        WHERE dph.ticker = ph.ticker
        ORDER BY dph.trading_date DESC
        LIMIT 1
    ) lp ON TRUE
    WHERE up.user_id = p_user_id
      AND ph.quantity > 0
    ORDER BY ph.holding_id;
$$;

COMMENT ON FUNCTION calculate_portfolio_value(INTEGER) IS
'Returns per-holding current market value for active holdings (quantity > 0) using latest close price. Evaluates ownership through user_portfolio in Pure 3NF.';
