-- ============================================================================
-- Function: get_latest_stock_price(p_ticker TEXT)
-- Returns:  NUMERIC  – latest closing price, or NULL if no history exists
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Fetch the most recent closing price for the given ticker by selecting
--   the row with the maximum trading_date in daily_price_history.
--   Returns NULL (not an error) when the ticker has no price history or
--   does not exist in the company table.
--
-- Business rules:
--   - The ticker is case-sensitive (matches the imported dataset format, e.g. 'TCS.NS').
--   - If close_price itself is NULL on the latest row, NULL is returned.
--   - No exception is raised for unknown tickers; callers must check for NULL.
-- ============================================================================

CREATE OR REPLACE FUNCTION get_latest_stock_price(p_ticker TEXT)
RETURNS NUMERIC
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT close_price
    FROM daily_price_history
    WHERE ticker = p_ticker
    ORDER BY trading_date DESC
    LIMIT 1;
$$;

COMMENT ON FUNCTION get_latest_stock_price(TEXT) IS
'Returns the latest available closing price for a ticker, or NULL if no price history exists.';
