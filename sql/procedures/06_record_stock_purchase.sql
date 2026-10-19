-- ============================================================================
-- Procedure: record_stock_purchase(p_user_id, p_ticker, p_quantity, p_price, p_purchase_date)
-- Database:  stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Record a stock purchase for a user by:
--     1. Validating that the user and company exist.
--     2. Rejecting non-positive quantities or negative prices.
--     3. Inserting a BUY row into portfolio_transaction.
--     4. Creating a new portfolio_holding row if none exists for (user_id, ticker),
--        or updating quantity, invested_value and average_buy_price on the
--        existing holding using weighted-average cost.
--
-- Cost-basis update formula (weighted average):
--   new_invested_value  = old_invested_value  + (p_quantity × p_price)
--   new_quantity        = old_quantity         + p_quantity
--   new_avg_buy_price   = new_invested_value   / new_quantity
--
-- Schema notes (inspected 2026-10-19):
--   portfolio_holding PK: holding_id (SERIAL)
--   Composite unique: UNIQUE (holding_id, user_id)  — used by FK from transaction
--   portfolio_transaction FK: (holding_id, user_id) → portfolio_holding(holding_id, user_id)
--   One holding row per (user_id, ticker) is enforced by application logic here;
--   there is no schema-level UNIQUE (user_id, ticker) constraint.
--
-- Idempotency note:
--   There is no natural deduplication key in the current schema (no external
--   reference ID column). Callers should avoid duplicate calls; this procedure
--   does NOT silently ignore repeated identical calls.
--
-- Parameters:
--   p_user_id      – app_user.user_id (must exist)
--   p_ticker       – company.ticker   (must exist, e.g. 'TCS.NS')
--   p_quantity     – shares to purchase (must be > 0)
--   p_price        – price per share   (must be >= 0)
--   p_purchase_date – date of purchase (defaults to CURRENT_DATE if NULL)
--
-- Error codes raised:
--   P0001 – user not found
--   P0001 – company not found
--   22023 – non-positive quantity
--   22023 – negative price
-- ============================================================================

CREATE OR REPLACE PROCEDURE record_stock_purchase(
    p_user_id      INTEGER,
    p_ticker       TEXT,
    p_quantity     NUMERIC,
    p_price        NUMERIC,
    p_purchase_date DATE DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_purchase_date     DATE;
    v_holding_id        INTEGER;
    v_old_quantity      NUMERIC;
    v_old_invested      NUMERIC;
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

    -- Resolve purchase date
    v_purchase_date := COALESCE(p_purchase_date, CURRENT_DATE);

    -- -----------------------------------------------------------------------
    -- 2. Upsert portfolio_holding
    --    Strategy: SELECT FOR UPDATE to lock the existing row if present,
    --              then INSERT or UPDATE atomically within this transaction.
    -- -----------------------------------------------------------------------
    SELECT holding_id, quantity, invested_value
    INTO   v_holding_id, v_old_quantity, v_old_invested
    FROM   portfolio_holding
    WHERE  user_id = p_user_id
      AND  ticker  = p_ticker
    FOR UPDATE;           -- lock to prevent concurrent double-INSERT

    IF FOUND THEN
        -- Update existing holding using weighted-average cost
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
        -- Create new holding row
        v_new_quantity  := p_quantity;
        v_new_invested  := p_quantity * p_price;
        v_new_avg_price := p_price;

        INSERT INTO portfolio_holding
            (user_id, ticker, quantity, invested_value, average_buy_price, purchase_date)
        VALUES
            (p_user_id, p_ticker, v_new_quantity, v_new_invested, v_new_avg_price, v_purchase_date)
        RETURNING holding_id INTO v_holding_id;
    END IF;

    -- -----------------------------------------------------------------------
    -- 3. Insert BUY transaction
    --    The composite FK (holding_id, user_id) is satisfied because we just
    --    confirmed/created holding_id for this user_id above.
    -- -----------------------------------------------------------------------
    INSERT INTO portfolio_transaction
        (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_holding_id, p_user_id, p_ticker, 'BUY', v_purchase_date, p_price, p_quantity);

    -- Procedure commits when called outside an explicit transaction block.
    -- If called inside BEGIN/COMMIT, the caller controls atomicity.
END;
$$;

COMMENT ON PROCEDURE record_stock_purchase(INTEGER, TEXT, NUMERIC, NUMERIC, DATE) IS
'Records a stock purchase: validates inputs, inserts a BUY transaction, and creates or weighted-average-updates the portfolio_holding. Rolls back atomically on any failure.';
