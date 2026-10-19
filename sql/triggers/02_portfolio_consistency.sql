-- ============================================================================
-- Trigger:  trg_portfolio_transaction_consistency
-- Table:    portfolio_transaction
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Maintains transactional, relational, and business integrity for portfolio operations:
--     1. Validates holding relationship and cross-table ticker alignment.
--        Automatically associates transactions with existing holdings when holding_id is omitted.
--     2. Accurately validates SELL transactions against remaining available shares:
--        - Source of truth: Total acquired shares minus committed SELL transactions.
--        - Total acquired shares is derived from BUY transactions in portfolio_transaction,
--          or from the holding baseline if initialized directly without transaction history.
--        - Accounts for previous BUYs and SELLs without double-counting.
--        - Correctly handles UPDATE operations on existing SELL transactions.
--        - Rejects overselling with standard error code 22023.
--     3. Serializes concurrent operations using row-level locking (SELECT ... FOR UPDATE)
--        on portfolio_holding to eliminate race conditions.
--     4. Enforces ledger immutability on UPDATE: prevents modification of core fields
--        (transaction_id, user_id, ticker, transaction_type).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Trigger Function
-- ----------------------------------------------------------------------------
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
    -- 1. Immutability checks on UPDATE
    IF (TG_OP = 'UPDATE') THEN
        IF NEW.transaction_id <> OLD.transaction_id THEN
            RAISE EXCEPTION 'Cannot modify transaction_id on existing transaction.'
                USING ERRCODE = '23514'; -- check_violation
        END IF;

        IF NEW.user_id <> OLD.user_id THEN
            RAISE EXCEPTION 'Cannot modify user_id on existing transaction.'
                USING ERRCODE = '23514'; -- check_violation
        END IF;

        IF NEW.ticker <> OLD.ticker THEN
            RAISE EXCEPTION 'Cannot modify ticker on existing transaction.'
                USING ERRCODE = '23514'; -- check_violation
        END IF;

        IF NEW.transaction_type <> OLD.transaction_type THEN
            RAISE EXCEPTION 'Cannot modify transaction_type on existing transaction.'
                USING ERRCODE = '23514'; -- check_violation
        END IF;
    END IF;

    -- 2. Resolve holding and acquire row lock for concurrency serialization
    IF NEW.holding_id IS NOT NULL THEN
        SELECT holding_id, user_id, ticker, quantity
        INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
        FROM portfolio_holding
        WHERE holding_id = NEW.holding_id
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Holding with holding_id % does not exist.', NEW.holding_id
                USING ERRCODE = '23503'; -- foreign_key_violation
        END IF;

        IF v_holding_user <> NEW.user_id THEN
            RAISE EXCEPTION 'Holding % belongs to user %, not user %.',
                NEW.holding_id, v_holding_user, NEW.user_id
                USING ERRCODE = '23514'; -- check_violation
        END IF;

        IF v_holding_ticker <> NEW.ticker THEN
            RAISE EXCEPTION 'Transaction ticker ''%'' does not match holding ticker ''%'' (holding_id: %).',
                NEW.ticker, v_holding_ticker, NEW.holding_id
                USING ERRCODE = '23514'; -- check_violation
        END IF;
    ELSE
        -- Automatically resolve holding if holding_id omitted but user_id and ticker exist
        SELECT holding_id, user_id, ticker, quantity
        INTO v_holding_id, v_holding_user, v_holding_ticker, v_holding_quantity
        FROM portfolio_holding
        WHERE user_id = NEW.user_id AND ticker = NEW.ticker
        FOR UPDATE;

        IF FOUND THEN
            NEW.holding_id := v_holding_id;
        END IF;
    END IF;

    -- 3. Validate SELL transaction does not exceed remaining available shares
    IF NEW.transaction_type = 'SELL' THEN
        -- If no holding exists, the user owns 0 shares
        IF NEW.holding_id IS NULL THEN
            RAISE EXCEPTION 'Insufficient shares to sell: user % owns no holdings of %.',
                NEW.user_id, NEW.ticker
                USING ERRCODE = '22023'; -- invalid_parameter_value
        END IF;

        -- Sum explicit BUY transactions for this holding
        SELECT COALESCE(SUM(quantity), 0)
        INTO v_total_bought
        FROM portfolio_transaction
        WHERE holding_id = NEW.holding_id
          AND transaction_type = 'BUY';

        -- Sum previous SELL transactions for this holding.
        -- When updating an existing SELL transaction, exclude this transaction_id.
        SELECT COALESCE(SUM(quantity), 0)
        INTO v_already_sold
        FROM portfolio_transaction
        WHERE holding_id = NEW.holding_id
          AND transaction_type = 'SELL'
          AND (TG_OP = 'INSERT' OR transaction_id <> NEW.transaction_id);

        -- If explicit BUY transactions exist, they form the ledger acquired pool.
        -- If no BUY transactions exist (direct holding insertion), holding baseline quantity is used.
        IF v_total_bought > 0 THEN
            v_acquired_pool := v_total_bought;
        ELSE
            v_acquired_pool := v_holding_quantity;
        END IF;

        v_available_shares := v_acquired_pool - v_already_sold;

        IF NEW.quantity > v_available_shares THEN
            RAISE EXCEPTION 'Insufficient shares to sell: attempted to sell %, but only % shares available for holding % (acquired total: %, already sold: %).',
                NEW.quantity, v_available_shares, NEW.holding_id, v_acquired_pool, v_already_sold
                USING ERRCODE = '22023'; -- invalid_parameter_value
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION fn_enforce_portfolio_transaction_consistency() IS
'Validates ticker consistency, serializes concurrency via row locks, calculates remaining shares accounting for previous sales and updates, and enforces immutability.';

-- ----------------------------------------------------------------------------
-- 2. Trigger Definition
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_portfolio_transaction_consistency ON portfolio_transaction;

CREATE TRIGGER trg_portfolio_transaction_consistency
BEFORE INSERT OR UPDATE ON portfolio_transaction
FOR EACH ROW
EXECUTE FUNCTION fn_enforce_portfolio_transaction_consistency();
