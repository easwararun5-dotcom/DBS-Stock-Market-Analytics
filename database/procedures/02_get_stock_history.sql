-- ============================================================================
-- Function: get_stock_history(p_ticker TEXT, p_start_date DATE, p_end_date DATE)
-- Returns:  TABLE – historical price rows for the ticker in the date range
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Return ordered historical price records (date, OHLCV + daily_return)
--   for the requested ticker and date range, inclusive on both ends.
--
-- Business rules:
--   - p_start_date must not be after p_end_date; if violated, raises SQLSTATE 22023.
--   - If the ticker does not exist or has no rows in the range, zero rows are returned.
--   - Results are ordered ascending by trading_date.
--   - daily_return may be NULL for the earliest rows where it could not be computed.
-- ============================================================================

CREATE OR REPLACE FUNCTION get_stock_history(
    p_ticker     TEXT,
    p_start_date DATE,
    p_end_date   DATE
)
RETURNS TABLE (
    trading_date  DATE,
    open_price    NUMERIC,
    high_price    NUMERIC,
    low_price     NUMERIC,
    close_price   NUMERIC,
    volume        BIGINT,
    daily_return  NUMERIC
)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
AS $$
BEGIN
    -- Validate date range
    IF p_start_date > p_end_date THEN
        RAISE EXCEPTION 'p_start_date (%) must not be after p_end_date (%).', p_start_date, p_end_date
            USING ERRCODE = '22023';
    END IF;

    RETURN QUERY
    SELECT
        dph.trading_date,
        dph.open_price,
        dph.high_price,
        dph.low_price,
        dph.close_price,
        dph.volume,
        dph.daily_return
    FROM daily_price_history dph
    WHERE dph.ticker       = p_ticker
      AND dph.trading_date BETWEEN p_start_date AND p_end_date
    ORDER BY dph.trading_date ASC;
END;
$$;

COMMENT ON FUNCTION get_stock_history(TEXT, DATE, DATE) IS
'Returns daily OHLCV and daily_return for a ticker within an inclusive date range, ordered ascending. Raises SQLSTATE 22023 if start_date > end_date.';
