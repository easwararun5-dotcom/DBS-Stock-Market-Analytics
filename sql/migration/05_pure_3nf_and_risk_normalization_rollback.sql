-- ============================================================================
-- Migration Rollback: 05_pure_3nf_and_risk_normalization_rollback.sql
-- Database:           stock_market_db (PostgreSQL port 5435)
-- Purpose:            Reverts 05_pure_3nf_and_risk_normalization.sql to exact previous schema.
-- ============================================================================
-- Academic Rationale & Reversibility Analysis:
--   1. Restoring portfolio_holding.user_id:
--      - Fully reversible because user_portfolio.user_id uniquely identifies the owner.
--      - Backfills user_id from user_portfolio before adding NOT NULL and UNIQUE constraints.
--   2. Restoring composite foreign key (holding_id, user_id):
--      - Reinstates uq_holding_user on portfolio_holding.
--      - Re-establishes fk_transaction_holding_user on portfolio_transaction.
--   3. Restoring previous stored procedures, functions, and triggers:
--      - Reverts signatures and query filters to original 2NF state.
--   4. Lossless Post-Migration Preservation:
--      - Any new risk analyses or sector allocations created in the normalized schema
--        post-migration are dynamically reconstructed and backfilled into JSONB
--        before dropping portfolio_risk_sector_allocation, guaranteeing zero data loss.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- Check 1.0: Ensure migration 05 is applied before attempting rollback
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'portfolio_holding' AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'ROLLBACK ABORTED: Migration 05 rollback cannot run because portfolio_holding.user_id is already present.'
            USING ERRCODE = '55000';
    END IF;
    RAISE NOTICE 'Pre-check PASSED: Migrated schema is ready for rollback.';
END;
$$;

-- ----------------------------------------------------------------------------
-- STEP 1: RESTORE JSONB SECTOR CONCENTRATION & RETIRE 1NF OBJECTS
-- ----------------------------------------------------------------------------

-- 1.1 Ensure sector_concentration column exists on portfolio_risk_analysis
ALTER TABLE portfolio_risk_analysis
    ADD COLUMN IF NOT EXISTS sector_concentration JSONB;

-- 1.2 Backfill/reconstruct JSONB sector_concentration from normalized child table
--     Guarantees that any new risk analyses or sector allocations inserted post-migration
--     are 100% preserved in the legacy JSONB representation without data loss.
UPDATE portfolio_risk_analysis pra
SET sector_concentration = alloc.jsonb_alloc
FROM (
    SELECT
        prsa.analysis_id,
        jsonb_object_agg(s.sector_name, prsa.concentration_pct) AS jsonb_alloc
    FROM portfolio_risk_sector_allocation prsa
    JOIN sector s ON prsa.sector_id = s.sector_id
    GROUP BY prsa.analysis_id
) alloc
WHERE pra.analysis_id = alloc.analysis_id;

-- 1.3 Drop view and normalized child table
DROP VIEW IF EXISTS v_portfolio_risk_analysis;
DROP TABLE IF EXISTS portfolio_risk_sector_allocation;

-- ----------------------------------------------------------------------------
-- STEP 2: RESTORE portfolio_holding.user_id AND CONSTRAINTS
-- ----------------------------------------------------------------------------

-- 2.1 Re-add user_id column
ALTER TABLE portfolio_holding
    ADD COLUMN IF NOT EXISTS user_id INT;

-- 2.2 Backfill user_id from owning user_portfolio
UPDATE portfolio_holding ph
SET user_id = up.user_id
FROM user_portfolio up
WHERE ph.portfolio_id = up.portfolio_id;

-- 2.3 Verify zero NULL user_ids before enforcing NOT NULL
DO $$
DECLARE
    v_orphaned INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_orphaned
    FROM portfolio_holding
    WHERE user_id IS NULL;

    IF v_orphaned > 0 THEN
        RAISE EXCEPTION 'ROLLBACK ABORTED: Found % holdings that could not be mapped back to a user.', v_orphaned;
    END IF;
END;
$$;

-- 2.4 Enforce NOT NULL and restore foreign key
ALTER TABLE portfolio_holding
    ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE portfolio_holding
    ADD CONSTRAINT portfolio_holding_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES app_user(user_id) ON DELETE CASCADE;

-- 2.5 Restore unique constraint on (holding_id, user_id)
ALTER TABLE portfolio_holding
    ADD CONSTRAINT uq_holding_user UNIQUE (holding_id, user_id);

CREATE INDEX IF NOT EXISTS idx_holding_user ON portfolio_holding(user_id);

-- 2.6 Drop 3NF unique constraint on (portfolio_id, ticker)
ALTER TABLE portfolio_holding
    DROP CONSTRAINT IF EXISTS uq_portfolio_holding_ticker;

-- 2.7 Allow nullable portfolio_id (matching pre-05 state)
ALTER TABLE portfolio_holding
    ALTER COLUMN portfolio_id DROP NOT NULL;

-- ----------------------------------------------------------------------------
-- STEP 3: RESTORE COMPOSITE FOREIGN KEY ON portfolio_transaction
-- ----------------------------------------------------------------------------
ALTER TABLE portfolio_transaction
    DROP CONSTRAINT IF EXISTS fk_transaction_holding;

ALTER TABLE portfolio_transaction
    ADD CONSTRAINT fk_transaction_holding_user
    FOREIGN KEY (holding_id, user_id)
    REFERENCES portfolio_holding(holding_id, user_id)
    ON DELETE SET NULL (holding_id);

-- ----------------------------------------------------------------------------
-- STEP 4: RESTORE PREVIOUS STORED PROCEDURES, FUNCTIONS & TRIGGERS
-- ----------------------------------------------------------------------------

-- 4.1 Restore calculate_portfolio_value
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
    JOIN company c ON c.ticker = ph.ticker
    LEFT JOIN LATERAL (
        SELECT dph.close_price
        FROM daily_price_history dph
        WHERE dph.ticker = ph.ticker
        ORDER BY dph.trading_date DESC
        LIMIT 1
    ) lp ON TRUE
    WHERE ph.user_id = p_user_id
      AND ph.quantity > 0
    ORDER BY ph.holding_id;
$$;

-- 4.2 Restore calculate_portfolio_profit_loss
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
    JOIN company c ON c.ticker = ph.ticker
    LEFT JOIN LATERAL (
        SELECT dph.close_price
        FROM daily_price_history dph
        WHERE dph.ticker = ph.ticker
        ORDER BY dph.trading_date DESC
        LIMIT 1
    ) lp ON TRUE
    WHERE ph.user_id = p_user_id
      AND ph.quantity > 0
    ORDER BY ph.holding_id;
$$;

-- 4.3 Restore record_stock_purchase
DROP PROCEDURE IF EXISTS record_stock_purchase(INTEGER, TEXT, NUMERIC, NUMERIC, DATE, INTEGER);

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

    v_purchase_date := COALESCE(p_purchase_date, CURRENT_DATE);

    SELECT holding_id, quantity, invested_value
    INTO   v_holding_id, v_old_quantity, v_old_invested
    FROM   portfolio_holding
    WHERE  user_id = p_user_id
      AND  ticker  = p_ticker
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
            (user_id, ticker, quantity, invested_value, average_buy_price, purchase_date)
        VALUES
            (p_user_id, p_ticker, v_new_quantity, v_new_invested, v_new_avg_price, v_purchase_date)
        RETURNING holding_id INTO v_holding_id;
    END IF;

    INSERT INTO portfolio_transaction
        (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_holding_id, p_user_id, p_ticker, 'BUY', v_purchase_date, p_price, p_quantity);
END;
$$;

-- 4.4 Restore record_stock_sale
DROP PROCEDURE IF EXISTS record_stock_sale(INTEGER, TEXT, NUMERIC, NUMERIC, DATE, INTEGER);

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

    v_sale_date := COALESCE(p_sale_date, CURRENT_DATE);

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

    IF p_quantity > v_old_quantity THEN
        RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but user % owns % shares of %.',
            p_quantity, p_user_id, v_old_quantity, p_ticker
            USING ERRCODE = '22023';
    END IF;

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

    INSERT INTO portfolio_transaction
        (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_holding_id, p_user_id, p_ticker, 'SELL', v_sale_date, p_price, p_quantity);
END;
$$;

-- 4.5 Restore fn_enforce_portfolio_transaction_consistency
CREATE OR REPLACE FUNCTION fn_enforce_portfolio_transaction_consistency()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_holding_id           INTEGER;
    v_holding_user         INTEGER;
    v_holding_ticker       TEXT;
    v_holding_quantity     NUMERIC;
    v_total_bought         NUMERIC;
    v_already_sold         NUMERIC;
    v_acquired_pool        NUMERIC;
    v_available_shares     NUMERIC;
BEGIN
    IF (TG_OP = 'UPDATE') THEN
        IF NEW.transaction_id <> OLD.transaction_id THEN
            RAISE EXCEPTION 'Cannot modify transaction_id on existing transaction.'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.user_id <> OLD.user_id THEN
            RAISE EXCEPTION 'Cannot modify user_id on existing transaction.'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.ticker <> OLD.ticker THEN
            RAISE EXCEPTION 'Cannot modify ticker on existing transaction.'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.transaction_type <> OLD.transaction_type THEN
            RAISE EXCEPTION 'Cannot modify transaction_type on existing transaction.'
                USING ERRCODE = '23514';
        END IF;
    END IF;

    IF NEW.holding_id IS NOT NULL THEN
        SELECT holding_id, user_id, ticker, quantity
        INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
        FROM portfolio_holding
        WHERE holding_id = NEW.holding_id
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Holding with holding_id % does not exist.', NEW.holding_id
                USING ERRCODE = '23503';
        END IF;

        IF v_holding_user <> NEW.user_id THEN
            RAISE EXCEPTION 'Holding % belongs to user %, not user %.',
                NEW.holding_id, v_holding_user, NEW.user_id
                USING ERRCODE = '23514';
        END IF;

        IF v_holding_ticker <> NEW.ticker THEN
            RAISE EXCEPTION 'Transaction ticker ''%'' does not match holding ticker ''%'' (holding_id: %).',
                NEW.ticker, v_holding_ticker, NEW.holding_id
                USING ERRCODE = '23514';
        END IF;
    ELSIF (TG_OP = 'INSERT') THEN
        SELECT holding_id, user_id, ticker, quantity
        INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
        FROM portfolio_holding
        WHERE user_id = NEW.user_id AND ticker = NEW.ticker
        FOR UPDATE;

        IF FOUND THEN
            NEW.holding_id := v_holding_id;
        END IF;
    END IF;

    IF NEW.transaction_type = 'SELL' THEN
        IF NEW.holding_id IS NULL THEN
            RAISE EXCEPTION 'Insufficient shares to sell: user % owns no holdings of %.',
                NEW.user_id, NEW.ticker
                USING ERRCODE = '22023';
        END IF;

        SELECT COALESCE(SUM(quantity), 0)
        INTO v_total_bought
        FROM portfolio_transaction
        WHERE holding_id = NEW.holding_id
          AND transaction_type = 'BUY';

        SELECT COALESCE(SUM(quantity), 0)
        INTO v_already_sold
        FROM portfolio_transaction
        WHERE holding_id = NEW.holding_id
          AND transaction_type = 'SELL'
          AND (TG_OP = 'INSERT' OR transaction_id <> NEW.transaction_id);

        IF v_total_bought > 0 THEN
            v_acquired_pool := v_total_bought;
        ELSE
            v_acquired_pool := v_holding_quantity;
        END IF;

        v_available_shares := v_acquired_pool - v_already_sold;

        IF NEW.quantity > v_available_shares THEN
            RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but only % shares available for holding % (acquired total: %, already sold: %).',
                NEW.quantity, v_available_shares, NEW.holding_id, v_acquired_pool, v_already_sold
                USING ERRCODE = '22023';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

COMMIT;
