-- ============================================================================
-- Procedure: record_stock_purchase(p_user_id, p_ticker, p_quantity, p_price, p_purchase_date, p_portfolio_id)
-- Database:  stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Record a stock purchase for a user by:
--     1. Validating that the user and company exist.
--     2. Rejecting non-positive quantities or negative prices.
--     3. Resolving the target portfolio (supports explicit portfolio_id or default user portfolio).
--     4. Creating a new portfolio_holding row if none exists for (portfolio_id, ticker),
--        or updating quantity, invested_value, and average_buy_price on the
--        existing holding using weighted-average cost basis (Pure 3NF).
--     5. Inserting a BUY row into portfolio_transaction.
--
-- Cost-basis update formula (weighted average):
--   new_invested_value  = old_invested_value  + (p_quantity × p_price)
--   new_quantity        = old_quantity         + p_quantity
--   new_avg_buy_price   = new_invested_value   / new_quantity
--
-- Schema notes (Pure 3NF):
--   portfolio_holding PK: holding_id (SERIAL)
--   portfolio_holding FK: portfolio_id -> user_portfolio(portfolio_id)
--   Composite unique: UNIQUE (portfolio_id, ticker)
--   portfolio_transaction FK: holding_id -> portfolio_holding(holding_id) ON DELETE SET NULL
-- ============================================================================

-- Drop legacy 5-parameter signature if present to avoid unintended overloading
DROP PROCEDURE IF EXISTS record_stock_purchase(INTEGER, TEXT, NUMERIC, NUMERIC, DATE);

CREATE OR REPLACE PROCEDURE record_stock_purchase(
    p_user_id       INTEGER,
    p_ticker        TEXT,
    p_quantity      NUMERIC,
    p_price         NUMERIC,
    p_purchase_date DATE DEFAULT NULL,
    p_portfolio_id  INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_purchase_date     DATE;
    v_portfolio_id      INTEGER;
    v_holding_id        INTEGER;
    v_old_quantity      NUMERIC;
    v_old_invested      NUMERIC;
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

    -- 2. Resolve portfolio_id: use explicitly passed or fetch/create default portfolio
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
            INSERT INTO user_portfolio (user_id, portfolio_name, cash_balance)
            VALUES (p_user_id, 'Main Portfolio', 100000.00)
            RETURNING portfolio_id INTO v_portfolio_id;
        END IF;
    END IF;

    v_purchase_date := COALESCE(p_purchase_date, CURRENT_DATE);

    -- 3. Upsert portfolio_holding using (portfolio_id, ticker)
    SELECT holding_id, quantity, invested_value
    INTO   v_holding_id, v_old_quantity, v_old_invested
    FROM   portfolio_holding
    WHERE  portfolio_id = v_portfolio_id
      AND  ticker       = p_ticker
    FOR UPDATE;

    IF FOUND THEN
        v_new_quantity  := v_old_quantity + p_quantity;
        v_new_invested  := v_old_invested + (p_quantity * p_price);
        v_new_avg_price := v_new_invested / v_new_quantity;

        UPDATE portfolio_holding
        SET
            quantity          = v_new_quantity,
            invested_value    = v_new_invested,
            average_buy_price = v_new_avg_price
        WHERE holding_id = v_holding_id;
    ELSE
        v_new_quantity  := p_quantity;
        v_new_invested  := p_quantity * p_price;
        v_new_avg_price := p_price;

        INSERT INTO portfolio_holding
            (portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date)
        VALUES
            (v_portfolio_id, p_ticker, v_new_quantity, v_new_invested, v_new_avg_price, v_purchase_date)
        RETURNING holding_id INTO v_holding_id;
    END IF;

    -- 4. Insert BUY transaction
    INSERT INTO portfolio_transaction
        (portfolio_id, holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_portfolio_id, v_holding_id, p_user_id, p_ticker, 'BUY', v_purchase_date, p_price, p_quantity);
END;
$$;

COMMENT ON PROCEDURE record_stock_purchase(INTEGER, TEXT, NUMERIC, NUMERIC, DATE, INTEGER) IS
'Records a stock purchase: validates inputs, inserts BUY transaction, and updates/inserts portfolio_holding using (portfolio_id, ticker) in Pure 3NF.';
