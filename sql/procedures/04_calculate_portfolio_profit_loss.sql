-- ============================================================================
-- Function: calculate_portfolio_profit_loss(p_user_id INTEGER)
-- Returns:  TABLE – per-holding P&L using invested_value as cost basis
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Calculate unrealised profit or loss for each of the user's active holdings
--   (quantity > 0).
--   - Market value is derived from the latest closing price × remaining quantity.
--   - Cost basis is taken from portfolio_holding.invested_value, which proportionately
--     reflects remaining shares after partial sales (maintained by record_stock_purchase
--     and record_stock_sale).
--
-- Pure 3NF Update:
--   Joins through user_portfolio on portfolio_id to identify holdings owned by p_user_id.
--
-- Business rules:
--   - Unrealised P&L = market_value - invested_value
--   - pnl_pct = (market_value - invested_value) / invested_value * 100
--   - If latest price is unavailable, market_value and pnl columns are NULL.
--   - invested_value = 0 makes pnl_pct undefined → returned as NULL.
--   - Returns empty set for users with no active holdings or unknown user IDs.
--   - Closed positions with 0 shares are excluded.
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_portfolio_profit_loss(p_user_id INTEGER)
RETURNS TABLE (
    holding_id        INTEGER,
    ticker            TEXT,
    company_name      TEXT,
    quantity          NUMERIC,
    average_buy_price NUMERIC,
    invested_value    NUMERIC,
    latest_price      NUMERIC,
    market_value      NUMERIC,
    unrealised_pnl    NUMERIC,
    pnl_pct           NUMERIC
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
        ph.average_buy_price,
        ph.invested_value,
        lp.close_price                                                  AS latest_price,
        ph.quantity * lp.close_price                                    AS market_value,
        (ph.quantity * lp.close_price) - ph.invested_value             AS unrealised_pnl,
        CASE
            WHEN ph.invested_value = 0 OR lp.close_price IS NULL THEN NULL
            ELSE ROUND(
                ((ph.quantity * lp.close_price - ph.invested_value) / ph.invested_value) * 100,
                2
            )
        END                                                              AS pnl_pct
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

COMMENT ON FUNCTION calculate_portfolio_profit_loss(INTEGER) IS
'Returns per-holding unrealised P&L using invested_value as cost basis and latest close price. Evaluates ownership through user_portfolio in Pure 3NF.';
