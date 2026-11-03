-- ============================================================================
-- Procedure: record_stock_sale(p_user_id, p_ticker, p_quantity, p_price, p_sale_date, p_portfolio_id)
-- Database:  stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Records a stock sale for a user by:
--     1. Validating user, ticker, quantity, and price inputs.
--     2. Resolving target portfolio (explicit portfolio_id or user's default portfolio).
--     3. Safely locking the user's holding using SELECT ... FOR UPDATE on (portfolio_id, ticker).
--     4. Validating that the user owns sufficient shares (rejecting overselling).
--     5. Updating portfolio_holding:
--        - Reduces quantity by p_quantity.
--        - Preserves the weighted-average buy price for remaining shares.
--        - Proportionately reduces invested_value (cost basis).
--        - If completely sold (quantity reaches 0), resets invested_value
--          and average_buy_price to 0 while preserving the holding row.
--     6. Inserting a SELL row into portfolio_transaction, which enlists in
--        trg_portfolio_transaction_audit and trg_portfolio_transaction_consistency.
-- ============================================================================

-- Drop legacy 5-parameter signature if present to avoid unintended overloading
DROP PROCEDURE IF EXISTS record_stock_sale(INTEGER, TEXT, NUMERIC, NUMERIC, DATE);

CREATE OR REPLACE PROCEDURE record_stock_sale(
    p_user_id       INTEGER,
    p_ticker        TEXT,
    p_quantity      NUMERIC,
    p_price         NUMERIC,
    p_sale_date     DATE DEFAULT NULL,
    p_portfolio_id  INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sale_date         DATE;
    v_portfolio_id      INTEGER;
    v_holding_id        INTEGER;
    v_old_quantity      NUMERIC;
    v_old_invested      NUMERIC;
    v_old_avg_price     NUMERIC;
    v_new_quantity      NUMERIC;
    v_new_invested      NUMERIC;
    v_new_avg_price     NUMERIC;
BEGIN
    -- 1. Input validation
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'p_quantity must be greater than 0; received %.', p_quantity
            USING ERRCODE = '22023';
    END IF;

    IF p_price < 0 THEN
        RAISE EXCEPTION 'p_price must be >= 0; received %.', p_price
            USING ERRCODE = '22023';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM app_user WHERE user_id = p_user_id) THEN
        RAISE EXCEPTION 'User with user_id % does not exist.', p_user_id
            USING ERRCODE = 'P0001';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM company WHERE ticker = p_ticker) THEN
        RAISE EXCEPTION 'Company with ticker ''%'' does not exist.', p_ticker
            USING ERRCODE = 'P0001';
    END IF;

    -- 2. Resolve portfolio_id: use explicit or find user default portfolio
    IF p_portfolio_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM user_portfolio WHERE portfolio_id = p_portfolio_id AND user_id = p_user_id) THEN
            RAISE EXCEPTION 'Portfolio % does not belong to user %.', p_portfolio_id, p_user_id
                USING ERRCODE = '23503';
        END IF;
        v_portfolio_id := p_portfolio_id;
    ELSE
        SELECT portfolio_id INTO v_portfolio_id
        FROM user_portfolio
        WHERE user_id = p_user_id
        ORDER BY portfolio_id ASC
        LIMIT 1;

        IF v_portfolio_id IS NULL THEN
            RAISE EXCEPTION 'User % has no active portfolios.', p_user_id
                USING ERRCODE = '22023';
        END IF;
    END IF;

    v_sale_date := COALESCE(p_sale_date, CURRENT_DATE);

    -- 3. Lock holding row using (portfolio_id, ticker)
    SELECT holding_id, quantity, invested_value, average_buy_price
    INTO   v_holding_id, v_old_quantity, v_old_invested, v_old_avg_price
    FROM   portfolio_holding
    WHERE  portfolio_id = v_portfolio_id
      AND  ticker       = p_ticker
    FOR UPDATE;

    IF NOT FOUND OR v_old_quantity <= 0 THEN
        RAISE EXCEPTION 'User % owns no shares of % in portfolio % to sell.', p_user_id, p_ticker, v_portfolio_id
            USING ERRCODE = '22023';
    END IF;

    -- Validate share availability
    IF p_quantity > v_old_quantity THEN
        RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but portfolio % owns % shares of %.',
            p_quantity, v_portfolio_id, v_old_quantity, p_ticker
            USING ERRCODE = '22023';
    END IF;

    -- 4. Update portfolio_holding (Quantity and Cost Basis)
    v_new_quantity := v_old_quantity - p_quantity;

    IF v_new_quantity = 0 THEN
        v_new_invested  := 0.00;
        v_new_avg_price := 0.0000;
    ELSE
        v_new_avg_price := v_old_avg_price;
        v_new_invested  := ROUND(v_new_quantity * v_new_avg_price, 2);
    END IF;

    UPDATE portfolio_holding
    SET
        quantity          = v_new_quantity,
        invested_value    = v_new_invested,
        average_buy_price = v_new_avg_price
    WHERE holding_id = v_holding_id;

    -- 5. Insert SELL transaction
    INSERT INTO portfolio_transaction
        (portfolio_id, holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_portfolio_id, v_holding_id, p_user_id, p_ticker, 'SELL', v_sale_date, p_price, p_quantity);
END;
$$;

COMMENT ON PROCEDURE record_stock_sale(INTEGER, TEXT, NUMERIC, NUMERIC, DATE, INTEGER) IS
'Records a stock sale: validates inputs, locks holding, prevents overselling, reduces quantity and cost basis, and logs a SELL transaction in Pure 3NF.';
