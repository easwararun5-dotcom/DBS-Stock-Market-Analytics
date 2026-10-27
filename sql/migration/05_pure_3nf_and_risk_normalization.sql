-- ============================================================================
-- Migration: 05_pure_3nf_and_risk_normalization.sql
-- Database:  stock_market_db (PostgreSQL port 5435)
-- Purpose:   Achieve Pure 3NF for portfolio_holding and 1NF for risk analysis.
-- ============================================================================
-- Academic Rationale & Invariants:
--   1. Pure 3NF in portfolio_holding:
--      - portfolio_holding.user_id is transitively dependent via:
--        holding_id -> portfolio_id -> user_id (since portfolio_id is the PK of user_portfolio).
--      - Removing user_id eliminates this transitive dependency.
--      - portfolio_id is enforced as NOT NULL.
--      - Enforces UNIQUE (portfolio_id, ticker) to guarantee 1:1 holding aggregation per stock.
--
--   2. Immutable Ledger Preservation in portfolio_transaction:
--      - Drop composite constraint fk_transaction_holding_user.
--      - Add fk_transaction_holding FOREIGN KEY (holding_id)
--        REFERENCES portfolio_holding(holding_id) ON DELETE SET NULL.
--      - When a holding is closed or deleted, transaction records preserve full history:
--        transaction_id, portfolio_id, user_id, ticker, transaction_type, transaction_date, price, quantity.
--
--   3. Relational 1NF in portfolio_risk_analysis:
--      - Create child table portfolio_risk_sector_allocation(analysis_id, sector_id, concentration_pct).
--      - Validate and migrate sector allocations from existing JSONB column.
--      - Strictly fail on unmatched or ambiguous sector names (NO silent skipping or ON CONFLICT DO NOTHING).
--      - Verify source vs destination row counts and allocation sums.
--      - Preserve sector_concentration JSONB during this migration for zero downtime.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ----------------------------------------------------------------------------
-- STEP 1: PRE-MIGRATION DATA INTEGRITY VALIDATION
-- ----------------------------------------------------------------------------

-- Check 1.0: Ensure migration has not already been applied
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'portfolio_holding' AND column_name = 'user_id'
    ) THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Migration 05 has already been applied (portfolio_holding.user_id does not exist).'
            USING ERRCODE = '55000';
    END IF;
    RAISE NOTICE 'Pre-check PASSED: Base schema is ready for Migration 05.';
END;
$$;

-- Check 1.1: Ensure no holding has a NULL portfolio_id
DO $$
DECLARE
    v_null_portfolios INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_null_portfolios
    FROM portfolio_holding
    WHERE portfolio_id IS NULL;

    IF v_null_portfolios > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % portfolio_holding rows with NULL portfolio_id.', v_null_portfolios
            USING ERRCODE = '23502';
    END IF;
    RAISE NOTICE 'Pre-check PASSED: Zero holdings with NULL portfolio_id.';
END;
$$;

-- Check 1.2: Ensure no duplicate (portfolio_id, ticker) positions exist
DO $$
DECLARE
    v_duplicates INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_duplicates
    FROM (
        SELECT portfolio_id, ticker
        FROM portfolio_holding
        GROUP BY portfolio_id, ticker
        HAVING COUNT(*) > 1
    ) dupes;

    IF v_duplicates > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % duplicate (portfolio_id, ticker) holding pairs.', v_duplicates
            USING ERRCODE = '23505';
    END IF;
    RAISE NOTICE 'Pre-check PASSED: Zero duplicate (portfolio_id, ticker) pairs in portfolio_holding.';
END;
$$;

-- Check 1.3: Ensure portfolio_holding.user_id matches owning user_portfolio.user_id
DO $$
DECLARE
    v_user_mismatches INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_user_mismatches
    FROM portfolio_holding h
    JOIN user_portfolio p ON h.portfolio_id = p.portfolio_id
    WHERE h.user_id <> p.user_id;

    IF v_user_mismatches > 0 THEN
        RAISE EXCEPTION 'MIGRATION ABORTED: Found % holdings where user_id does not match owning user_portfolio.user_id.', v_user_mismatches
            USING ERRCODE = '23514';
    END IF;
    RAISE NOTICE 'Pre-check PASSED: All holding user_ids match owning portfolio user_ids.';
END;
$$;


-- ----------------------------------------------------------------------------
-- STEP 2: UPDATE STORED PROCEDURES, FUNCTIONS & TRIGGERS BEFORE DROPPING user_id
-- (Ensures no active database object references a column that has been dropped)
-- ----------------------------------------------------------------------------

-- 2.1 Calculate Portfolio Value (Function)
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

-- 2.2 Calculate Portfolio Profit/Loss (Function)
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

-- 2.3 Record Stock Purchase (Procedure)
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

    -- Resolve portfolio_id: use provided or find user's primary/first portfolio
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

    -- Upsert holding using (portfolio_id, ticker)
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

    -- Record transaction
    INSERT INTO portfolio_transaction
        (portfolio_id, holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_portfolio_id, v_holding_id, p_user_id, p_ticker, 'BUY', v_purchase_date, p_price, p_quantity);
END;
$$;

-- 2.4 Record Stock Sale (Procedure)
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

    -- Lock holding row using (portfolio_id, ticker)
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

    IF p_quantity > v_old_quantity THEN
        RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but portfolio % owns % shares of %.',
            p_quantity, v_portfolio_id, v_old_quantity, p_ticker
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

    -- Record transaction
    INSERT INTO portfolio_transaction
        (portfolio_id, holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES
        (v_portfolio_id, v_holding_id, p_user_id, p_ticker, 'SELL', v_sale_date, p_price, p_quantity);
END;
$$;

-- 2.5 Trigger Function for Portfolio Consistency
CREATE OR REPLACE FUNCTION fn_enforce_portfolio_transaction_consistency()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_holding_id           INTEGER;
    v_holding_user         INTEGER;
    v_holding_ticker       TEXT;
    v_holding_quantity     NUMERIC;
    v_holding_portfolio    INTEGER;
    v_total_bought         NUMERIC;
    v_already_sold         NUMERIC;
    v_acquired_pool        NUMERIC;
    v_available_shares     NUMERIC;
BEGIN
    -- 1. Immutability checks on UPDATE
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

    -- 2. Resolve holding and acquire row lock for concurrency serialization
    IF NEW.holding_id IS NOT NULL THEN
        SELECT h.holding_id, up.user_id, h.ticker, h.quantity, h.portfolio_id
        INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity, v_holding_portfolio
        FROM portfolio_holding h
        JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
        WHERE h.holding_id = NEW.holding_id
        FOR UPDATE OF h;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Holding with holding_id % does not exist.', NEW.holding_id
                USING ERRCODE = '23503';
        END IF;

        IF v_holding_user <> NEW.user_id THEN
            RAISE EXCEPTION 'Holding % belongs to user %, not user %.',
                NEW.holding_id, v_holding_user, NEW.user_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.portfolio_id IS NOT NULL AND v_holding_portfolio <> NEW.portfolio_id THEN
            RAISE EXCEPTION 'Holding % belongs to portfolio %, not portfolio %.',
                NEW.holding_id, v_holding_portfolio, NEW.portfolio_id
                USING ERRCODE = '23514';
        END IF;

        IF v_holding_ticker <> NEW.ticker THEN
            RAISE EXCEPTION 'Transaction ticker ''%'' does not match holding ticker ''%'' (holding_id: %).',
                NEW.ticker, v_holding_ticker, NEW.holding_id
                USING ERRCODE = '23514';
        END IF;

        IF NEW.portfolio_id IS NULL THEN
            NEW.portfolio_id := v_holding_portfolio;
        END IF;
    ELSIF (TG_OP = 'INSERT') THEN
        -- Automatically resolve holding on INSERT if holding_id omitted but portfolio_id/user_id and ticker exist
        IF NEW.portfolio_id IS NOT NULL THEN
            SELECT h.holding_id, up.user_id, h.ticker, h.quantity
            INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
            FROM portfolio_holding h
            JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
            WHERE h.portfolio_id = NEW.portfolio_id AND h.ticker = NEW.ticker
            FOR UPDATE OF h;
        ELSE
            SELECT h.holding_id, up.user_id, h.ticker, h.quantity
            INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
            FROM portfolio_holding h
            JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
            WHERE up.user_id = NEW.user_id AND h.ticker = NEW.ticker
            ORDER BY h.holding_id ASC
            LIMIT 1
            FOR UPDATE OF h;
        END IF;

        IF FOUND THEN
            NEW.holding_id := v_holding_id;
        END IF;
    END IF;

    -- 3. Validate SELL transaction does not exceed remaining available shares
    -- Validates on INSERT or when quantity changes (preserves ledger on ON DELETE SET NULL)
    IF NEW.transaction_type = 'SELL' AND (TG_OP = 'INSERT' OR NEW.quantity <> OLD.quantity) THEN
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


-- ----------------------------------------------------------------------------
-- STEP 3: CONVERT portfolio_holding TO PURE 3NF & REDESIGN TRANSACTIONS
-- ----------------------------------------------------------------------------

-- 3.1 Enforce NOT NULL on portfolio_id
ALTER TABLE portfolio_holding
    ALTER COLUMN portfolio_id SET NOT NULL;

-- 3.2 Add UNIQUE (portfolio_id, ticker) constraint
ALTER TABLE portfolio_holding
    ADD CONSTRAINT uq_portfolio_holding_ticker UNIQUE (portfolio_id, ticker);

-- 3.3 Replace composite foreign key on portfolio_transaction
ALTER TABLE portfolio_transaction
    DROP CONSTRAINT IF EXISTS fk_transaction_holding_user;

ALTER TABLE portfolio_holding
    DROP CONSTRAINT IF EXISTS uq_holding_user;

ALTER TABLE portfolio_transaction
    ADD CONSTRAINT fk_transaction_holding
    FOREIGN KEY (holding_id)
    REFERENCES portfolio_holding(holding_id)
    ON DELETE SET NULL;

-- 3.4 Drop the transitive dependency: portfolio_holding.user_id
-- Drop foreign key constraint on user_id first
ALTER TABLE portfolio_holding
    DROP CONSTRAINT IF EXISTS portfolio_holding_user_id_fkey;

-- Drop index on user_id if present
DROP INDEX IF EXISTS idx_holding_user;
DROP INDEX IF EXISTS idx_portfolio_holding_user_id;

-- Drop user_id column to complete 3NF
ALTER TABLE portfolio_holding
    DROP COLUMN user_id;


-- ----------------------------------------------------------------------------
-- STEP 4: RELATIONAL 1NF SECTOR RISK ALLOCATION TABLE & STRICT MIGRATION
-- ----------------------------------------------------------------------------

-- 4.1 Create normalized child table
CREATE TABLE IF NOT EXISTS portfolio_risk_sector_allocation (
    analysis_id       INTEGER NOT NULL REFERENCES portfolio_risk_analysis(analysis_id) ON DELETE CASCADE,
    sector_id         INTEGER NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT,
    concentration_pct NUMERIC(5,2) NOT NULL CHECK (concentration_pct >= 0 AND concentration_pct <= 100),
    CONSTRAINT pk_portfolio_risk_sector_allocation PRIMARY KEY (analysis_id, sector_id)
);

CREATE INDEX IF NOT EXISTS idx_risk_sector_alloc_sector 
    ON portfolio_risk_sector_allocation(sector_id);

COMMENT ON TABLE portfolio_risk_sector_allocation IS
'Normalized 1NF child table representing per-sector asset allocation percentages for portfolio risk analyses.';

-- 4.2 Lossless Validation and Migration from JSONB
DO $$
DECLARE
    v_unmatched_count INTEGER;
    v_source_keys     INTEGER;
    v_inserted_rows   INTEGER;
    v_source_sum      NUMERIC;
    v_dest_sum        NUMERIC;
BEGIN
    -- Check if any existing JSONB records exist
    SELECT COALESCE(SUM(jsonb_array_length(jsonb_path_query_array(sector_concentration, '$.*'))), 0)
    INTO v_source_keys
    FROM portfolio_risk_analysis
    WHERE sector_concentration IS NOT NULL AND sector_concentration <> '{}'::jsonb;

    IF v_source_keys > 0 THEN
        -- Validate that EVERY JSONB sector key maps to exactly one sector
        SELECT COUNT(*)
        INTO v_unmatched_count
        FROM (
            SELECT DISTINCT kv.key
            FROM portfolio_risk_analysis pra,
                 jsonb_each_text(pra.sector_concentration) kv
            LEFT JOIN sector s ON LOWER(s.sector_name) = LOWER(kv.key)
            WHERE s.sector_id IS NULL
        ) unmatched;

        IF v_unmatched_count > 0 THEN
            RAISE EXCEPTION 'MIGRATION ABORTED: Found % unmatched sector names in portfolio_risk_analysis JSONB data.', v_unmatched_count
                USING ERRCODE = '23503';
        END IF;

        -- Migrate data strictly (NO ON CONFLICT DO NOTHING)
        INSERT INTO portfolio_risk_sector_allocation (analysis_id, sector_id, concentration_pct)
        SELECT
            pra.analysis_id,
            s.sector_id,
            ROUND((kv.value)::NUMERIC, 2)
        FROM portfolio_risk_analysis pra,
             jsonb_each_text(pra.sector_concentration) kv
        JOIN sector s ON LOWER(s.sector_name) = LOWER(kv.key);

        GET DIAGNOSTICS v_inserted_rows = ROW_COUNT;

        -- Verify row count equality
        IF v_inserted_rows <> v_source_keys THEN
            RAISE EXCEPTION 'MIGRATION ABORTED: Count mismatch! Expected % keys, inserted % rows.', v_source_keys, v_inserted_rows;
        END IF;

        -- Verify numerical allocation totals equality
        SELECT COALESCE(SUM((kv.value)::NUMERIC), 0)
        INTO v_source_sum
        FROM portfolio_risk_analysis pra,
             jsonb_each_text(pra.sector_concentration) kv;

        SELECT COALESCE(SUM(concentration_pct), 0)
        INTO v_dest_sum
        FROM portfolio_risk_sector_allocation;

        IF ROUND(v_source_sum, 2) <> ROUND(v_dest_sum, 2) THEN
            RAISE EXCEPTION 'MIGRATION ABORTED: Sum mismatch! Source: %, Dest: %', v_source_sum, v_dest_sum;
        END IF;

        RAISE NOTICE 'Lossless Migration PASSED: Migrated % sector allocation rows with 100%% sum parity.', v_inserted_rows;
    ELSE
        RAISE NOTICE 'Migration PASSED: Zero existing JSONB risk records to migrate.';
    END IF;
END;
$$;

-- 4.3 Create backward-compatible reconstruction view
CREATE OR REPLACE VIEW v_portfolio_risk_analysis AS
SELECT
    pra.analysis_id,
    pra.user_id,
    pra.analysis_date,
    pra.sharpe_ratio,
    pra.volatility,
    pra.max_drawdown,
    pra.transaction_context,
    COALESCE(
        jsonb_object_agg(s.sector_name, prsa.concentration_pct)
        FILTER (WHERE s.sector_name IS NOT NULL),
        '{}'::jsonb
    ) AS sector_concentration
FROM portfolio_risk_analysis pra
LEFT JOIN portfolio_risk_sector_allocation prsa ON pra.analysis_id = prsa.analysis_id
LEFT JOIN sector s ON prsa.sector_id = s.sector_id
GROUP BY
    pra.analysis_id, pra.user_id, pra.analysis_date,
    pra.sharpe_ratio, pra.volatility, pra.max_drawdown, pra.transaction_context;

COMMENT ON VIEW v_portfolio_risk_analysis IS
'Reconstructs sector_concentration JSONB dynamically from normalized 1NF table portfolio_risk_sector_allocation.';

COMMIT;
