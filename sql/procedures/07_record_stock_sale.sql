-- ============================================================================
-- Procedure: record_stock_sale(p_user_id, p_ticker, p_quantity, p_price, p_sale_date)
-- Database:  stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Records a stock sale for a user by:
--     1. Validating user, ticker, quantity, and price inputs.
--     2. Safely locking the user's holding using SELECT ... FOR UPDATE.
--     3. Validating that the user owns sufficient shares (rejecting overselling).
--     4. Updating portfolio_holding:
--        - Reduces quantity by p_quantity.
--        - Preserves the weighted-average buy price for remaining shares.
--        - Proportionately reduces invested_value (cost basis).
--        - If completely sold (quantity reaches 0), resets invested_value
--          and average_buy_price to 0 while preserving the holding row.
--     5. Inserting a SELL row into portfolio_transaction, which automatically
--        enlists in trg_portfolio_transaction_audit and trg_portfolio_transaction_consistency.
--
-- Parameters:
--   p_user_id   – app_user.user_id (must exist)
--   p_ticker    – company.ticker (must exist, e.g. 'TCS.NS')
--   p_quantity  – shares to sell (must be > 0 and <= holding.quantity)
--   p_price     – execution price per share (must be >= 0)
--   p_sale_date – date of sale (defaults to CURRENT_DATE if NULL)
--
-- Error codes raised:
--   22023 – invalid parameter (non-positive quantity, negative price, or insufficient shares)
--   P0001 – entity not found (user or company does not exist)
-- ============================================================================

CREATE OR REPLACE PROCEDURE record_stock_sale(
    p_user_id      INTEGER,
    p_ticker       TEXT,
    p_quantity     NUMERIC,
    p_price        NUMERIC,
    p_sale_date    DATE DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sale_date         DATE;
    v_holding_id        INTEGER;
    v_old_quantity      NUMERIC;
    v_old_invested      NUMERIC;
    v_old_avg_price     NUMERIC;
    v_new_quantity      NUMERIC;
    v_new_invested      NUMERIC;
    v_new_avg_price     NUMERIC;
BEGIN
    -- -----------------------------------------------------------------------
    -- 1. Input validation
    -- -----------------------------------------------------------------------
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'p_quantity must be greater than 0; received %.', p_quantity
            USING ERRCODE = '22023';
    END IF;

    IF p_price < 0 THEN
        RAISE EXCEPTION 'p_price must be >= 0; received %.', p_price
            USING ERRCODE = '22023';
    END IF;

    -- Validate user exists
    IF NOT EXISTS (SELECT 1 FROM app_user WHERE user_id = p_user_id) THEN
        RAISE EXCEPTION 'User with user_id % does not exist.', p_user_id
            USING ERRCODE = 'P0001';
    END IF;

    -- Validate company exists
    IF NOT EXISTS (SELECT 1 FROM company WHERE ticker = p_ticker) THEN
        RAISE EXCEPTION 'Company with ticker ''%'' does not exist.', p_ticker
            USING ERRCODE = 'P0001';
    END IF;

    -- Resolve sale date
    v_sale_date := COALESCE(p_sale_date, CURRENT_DATE);

    -- -----------------------------------------------------------------------
    -- 2. Lock holding row to serialize concurrent sales
    -- -----------------------------------------------------------------------
    SELECT holding_id, quantity, invested_value, average_buy_price
    INTO   v_holding_id, v_old_quantity, v_old_invested, v_old_avg_price
    FROM   portfolio_holding
    WHERE  user_id = p_user_id
      AND  ticker  = p_ticker
    FOR UPDATE;

    IF NOT FOUND OR v_old_quantity <= 0 THEN
        RAISE EXCEPTION 'User % owns no shares of % to sell.', p_user_id, p_ticker
            USING ERRCODE = '22023';
    END IF;

    -- Validate share availability
    IF p_quantity > v_old_quantity THEN
        RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but user % owns % shares of %.',
            p_quantity, p_user_id, v_old_quantity, p_ticker
            USING ERRCODE = '22023';
    END IF;

    -- -----------------------------------------------------------------------
    -- 3. Update portfolio_holding (Quantity and Cost Basis)
    -- -----------------------------------------------------------------------
    v_new_quantity := v_old_quantity - p_quantity;

    IF v_new_quantity = 0 THEN
        -- Position completely closed
        v_new_invested  := 0.00;
        v_new_avg_price := 0.0000;
    ELSE
        -- Partial sale: weighted-average purchase price per share remains unchanged
        v_new_avg_price := v_old_avg_price;
        -- Invested cost basis reduces proportionately
        v_new_invested  := ROUND(v_new_quantity * v_new_avg_price, 2);
    END IF;

    UPDATE portfolio_holding
    SET
        quantity          = v_new_quantity,
        invested_value    = v_new_invested,
        average_buy_price = v_new_avg_price
    WHERE holding_id = v_holding_id;

    -- -----------------------------------------------------------------------
    -- 4. Insert SELL transaction
    -- -----------------------------------------------------------------------
    INSERT INTO portfolio_transaction
        (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_holding_id, p_user_id, p_ticker, 'SELL', v_sale_date, p_price, p_quantity);

END;
$$;

COMMENT ON PROCEDURE record_stock_sale(INTEGER, TEXT, NUMERIC, NUMERIC, DATE) IS
'Records a stock sale: validates inputs, locks holding, prevents overselling, proportionately reduces quantity and cost basis, and logs a SELL transaction.';
