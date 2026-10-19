-- ============================================================================
-- Function: get_watchlist_with_prices(p_user_id INTEGER)
-- Returns:  TABLE – watchlist entries enriched with latest price and sector
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   For each ticker on the user's watchlist, return company name, sector,
--   the user's alert_price, the latest closing price, and whether the alert
--   price has been reached. Tickers with no price history have NULL latest_price.
--
-- Business rules:
--   - Returns empty set for users with no watchlist entries or unknown user IDs.
--   - alert_price_triggered = TRUE when latest_price <= alert_price (price has
--     dropped to or below the buy alert target). NULL when either value is NULL.
--   - Results ordered by ticker alphabetically.
-- ============================================================================

CREATE OR REPLACE FUNCTION get_watchlist_with_prices(p_user_id INTEGER)
RETURNS TABLE (
    watchlist_id          INTEGER,
    ticker                TEXT,
    company_name          TEXT,
    sector_name           TEXT,
    alert_price           NUMERIC,
    latest_price          NUMERIC,
    latest_trading_date   DATE,
    alert_price_triggered BOOLEAN,
    added_at              TIMESTAMP
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT
        uw.watchlist_id,
        uw.ticker,
        c.company_name,
        s.sector_name,
        uw.alert_price,
        lp.close_price                                              AS latest_price,
        lp.trading_date                                             AS latest_trading_date,
        CASE
            WHEN uw.alert_price IS NULL OR lp.close_price IS NULL THEN NULL
            WHEN lp.close_price <= uw.alert_price                 THEN TRUE
            ELSE FALSE
        END::BOOLEAN                                                AS alert_price_triggered,
        uw.added_at
    FROM user_watchlist uw
    JOIN company c ON c.ticker = uw.ticker
    JOIN sector s  ON s.sector_id = c.sector_id
    LEFT JOIN LATERAL (
        SELECT dph.close_price, dph.trading_date
        FROM daily_price_history dph
        WHERE dph.ticker = uw.ticker
        ORDER BY dph.trading_date DESC
        LIMIT 1
    ) lp ON TRUE
    WHERE uw.user_id = p_user_id
    ORDER BY uw.ticker;
$$;

COMMENT ON FUNCTION get_watchlist_with_prices(INTEGER) IS
'Returns watchlisted companies with latest price, sector, and alert trigger status. alert_price_triggered is TRUE when latest_price <= alert_price.';
