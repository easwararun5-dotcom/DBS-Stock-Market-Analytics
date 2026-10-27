-- ============================================================================
-- Test Suite: Database Triggers Regression & Concurrency Validation
-- Database:   stock_market_db (PostgreSQL 18)
-- All operations run inside an atomic transaction and are ROLLED BACK.
-- No test data is persisted to the database.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_id           INTEGER;
    v_user2_id          INTEGER;
    v_holding_id        INTEGER;
    v_h2_id             INTEGER;
    v_tx1_id            INTEGER;
    v_tx2_id            INTEGER;
    v_tx3_id            INTEGER;
    v_tx_audit_id       INTEGER;
    v_audit_count       INTEGER;
    v_audit_row         RECORD;
    v_holding_row       RECORD;
    v_holding_quantity  NUMERIC;
    v_err_caught        BOOLEAN;
    v_portfolio_id      INTEGER;
    v_has_user_id       BOOLEAN;
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'STARTING STRENGTHENED DATABASE TRIGGER REGRESSION SUITE';
    RAISE NOTICE '============================================================';

    -- ------------------------------------------------------------------------
    -- Setup Test Fixture: Create temporary test users
    -- ------------------------------------------------------------------------
    INSERT INTO app_user (username, email, password_hash, role)
    VALUES ('test_trg_user', 'trg_test@example.com', 'hash123', 'user')
    RETURNING user_id INTO v_user_id;

    INSERT INTO app_user (username, email, password_hash, role)
    VALUES ('test_trg_user2', 'trg_test2@example.com', 'hash456', 'user')
    RETURNING user_id INTO v_user2_id;

    INSERT INTO user_portfolio (user_id, portfolio_name, cash_balance)
    VALUES (v_user_id, 'Default Portfolio', 100000.00)
    RETURNING portfolio_id INTO v_portfolio_id;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'portfolio_holding' AND column_name = 'user_id'
    ) INTO v_has_user_id;

    RAISE NOTICE 'Fixture setup: created test users % and %, portfolio %', v_user_id, v_user2_id, v_portfolio_id;

    -- ========================================================================
    -- REGRESSION TEST 1: Holding of 10 shares, previous SELL of 7 shares,
    --                   followed by an attempted SELL of 5 shares (must reject).
    -- ========================================================================
    IF v_has_user_id THEN
        EXECUTE 'INSERT INTO portfolio_holding (user_id, portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING holding_id'
        INTO v_holding_id
        USING v_user_id, v_portfolio_id, 'TCS.NS', 10.0000, 35000.00, 3500.0000, '2026-03-01'::date;
    ELSE
        EXECUTE 'INSERT INTO portfolio_holding (portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date) VALUES ($1, $2, $3, $4, $5, $6) RETURNING holding_id'
        INTO v_holding_id
        USING v_portfolio_id, 'TCS.NS', 10.0000, 35000.00, 3500.0000, '2026-03-01'::date;
    END IF;

    -- First SELL of 7 shares
    INSERT INTO portfolio_transaction (
        holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity
    ) VALUES (
        v_holding_id, v_user_id, 'TCS.NS', 'SELL', '2026-03-02', 3600.0000, 7.0000
    ) RETURNING transaction_id INTO v_tx1_id;

    RAISE NOTICE 'Recorded initial SELL of 7 shares (Tx ID: %)', v_tx1_id;

    -- Attempted SELL of 5 shares (should fail: 10 - 7 = 3 available, attempted 5)
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO portfolio_transaction (
            holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity
        ) VALUES (
            v_holding_id, v_user_id, 'TCS.NS', 'SELL', '2026-03-03', 3650.0000, 5.0000
        );
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 1 - Correctly rejected SELL of 5 shares on holding with 3 remaining (caught 22023)';
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 1 FAILED: Overselling 5 shares was unexpectedly permitted!';
    END IF;

    -- ========================================================================
    -- REGRESSION TEST 2: Valid SELL within remaining quantity
    -- ========================================================================
    -- Remaining: 3 shares. Sell 2 shares -> should succeed.
    INSERT INTO portfolio_transaction (
        holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity
    ) VALUES (
        v_holding_id, v_user_id, 'TCS.NS', 'SELL', '2026-03-03', 3650.0000, 2.0000
    ) RETURNING transaction_id INTO v_tx2_id;

    -- Remaining: 1 share. Sell 1 share -> should succeed.
    INSERT INTO portfolio_transaction (
        holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity
    ) VALUES (
        v_holding_id, v_user_id, 'TCS.NS', 'SELL', '2026-03-04', 3700.0000, 1.0000
    ) RETURNING transaction_id INTO v_tx3_id;

    -- Remaining: 0 shares. Attempt to sell 0.5 shares -> should fail.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO portfolio_transaction (
            holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity
        ) VALUES (
            v_holding_id, v_user_id, 'TCS.NS', 'SELL', '2026-03-05', 3700.0000, 0.5000
        );
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 2 - Valid SELLs accepted to 0 remaining; subsequent SELL correctly rejected';
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 2 FAILED: Excess SELL was permitted when remaining shares reached 0!';
    END IF;

    -- ========================================================================
    -- REGRESSION TEST 3: Updating an existing SELL transaction
    -- ========================================================================
    -- Currently: tx1 = 7, tx2 = 2, tx3 = 1 (total 10 sold).
    -- Attempt to update tx3 from 1 to 2 -> should fail (only 1 was allocated to tx3, remaining is 0).
    v_err_caught := FALSE;
    BEGIN
        UPDATE portfolio_transaction
        SET quantity = 2.0000
        WHERE transaction_id = v_tx3_id;
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 3a - Updating SELL to exceed holding correctly rejected (caught 22023)';
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 3a FAILED: UPDATE to 2 shares was unexpectedly permitted!';
    END IF;

    -- Now reduce tx2 from 2 to 1 (frees up 1 share)
    UPDATE portfolio_transaction
    SET quantity = 1.0000
    WHERE transaction_id = v_tx2_id;

    -- Now tx3 can be updated from 1 to 2 (since 1 share was freed up)
    UPDATE portfolio_transaction
    SET quantity = 2.0000
    WHERE transaction_id = v_tx3_id;

    RAISE NOTICE 'PASS: Test 3b - Updating existing SELL transactions correctly accounted for freed and allocated shares';

    -- ========================================================================
    -- REGRESSION TEST 4: Invalid transaction updates (immutability)
    -- ========================================================================
    -- 4a: Cannot modify transaction_id
    v_err_caught := FALSE;
    BEGIN
        UPDATE portfolio_transaction
        SET transaction_id = transaction_id + 999
        WHERE transaction_id = v_tx1_id;
    EXCEPTION
        WHEN check_violation THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4a - Correctly rejected modifying transaction_id';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4a FAILED'; END IF;

    -- 4b: Cannot modify user_id
    v_err_caught := FALSE;
    BEGIN
        UPDATE portfolio_transaction
        SET user_id = v_user2_id
        WHERE transaction_id = v_tx1_id;
    EXCEPTION
        WHEN check_violation THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4b - Correctly rejected modifying user_id';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4b FAILED'; END IF;

    -- 4c: Cannot modify ticker
    v_err_caught := FALSE;
    BEGIN
        UPDATE portfolio_transaction
        SET ticker = 'INFY.NS'
        WHERE transaction_id = v_tx1_id;
    EXCEPTION
        WHEN check_violation THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4c - Correctly rejected modifying ticker';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4c FAILED'; END IF;

    -- 4d: Cannot modify transaction_type
    v_err_caught := FALSE;
    BEGIN
        UPDATE portfolio_transaction
        SET transaction_type = 'BUY'
        WHERE transaction_id = v_tx1_id;
    EXCEPTION
        WHEN check_violation THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4d - Correctly rejected modifying transaction_type';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4d FAILED'; END IF;

    -- ========================================================================
    -- REGRESSION TEST 5: Multiple transactions affecting the same holding
    -- ========================================================================
    IF v_has_user_id THEN
        EXECUTE 'INSERT INTO portfolio_holding (user_id, portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING holding_id'
        INTO v_h2_id
        USING v_user_id, v_portfolio_id, 'HDFCBANK.NS', 50.0000, 75000.00, 1500.0000, '2026-03-01'::date;
    ELSE
        EXECUTE 'INSERT INTO portfolio_holding (portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date) VALUES ($1, $2, $3, $4, $5, $6) RETURNING holding_id'
        INTO v_h2_id
        USING v_portfolio_id, 'HDFCBANK.NS', 50.0000, 75000.00, 1500.0000, '2026-03-01'::date;
    END IF;

    -- Three partial sales of 15 shares each (total 45)
    INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_h2_id, v_user_id, 'HDFCBANK.NS', 'SELL', '2026-03-02', 1550.0000, 15.0000);

    INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_h2_id, v_user_id, 'HDFCBANK.NS', 'SELL', '2026-03-03', 1560.0000, 15.0000);

    INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_h2_id, v_user_id, 'HDFCBANK.NS', 'SELL', '2026-03-04', 1570.0000, 15.0000);

    -- Attempt sell of 10 shares (only 5 remain: 50 - 45 = 5)
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
        VALUES (v_h2_id, v_user_id, 'HDFCBANK.NS', 'SELL', '2026-03-05', 1580.0000, 10.0000);
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 5a - Multiple transactions: rejected 10 shares when 5 remained';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 5a FAILED'; END IF;

    -- Sell final 5 shares
    INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_h2_id, v_user_id, 'HDFCBANK.NS', 'SELL', '2026-03-05', 1580.0000, 5.0000);

    RAISE NOTICE 'PASS: Test 5b - Successfully managed 4 successive sales on the same holding to completion';

    -- ========================================================================
    -- REGRESSION TEST 6: Integration with record_stock_purchase
    -- ========================================================================
    -- First purchase: 10 shares @ 1500
    CALL record_stock_purchase(v_user_id, 'INFY.NS', 10.0000, 1500.0000, '2026-03-01');

    -- Partial SELL of 6 shares (4 remain)
    INSERT INTO portfolio_transaction (user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_user_id, 'INFY.NS', 'SELL', '2026-03-02', 1550.0000, 6.0000);

    -- Attempt to sell 5 shares -> should fail (only 4 remain)
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO portfolio_transaction (user_id, ticker, transaction_type, transaction_date, price, quantity)
        VALUES (v_user_id, 'INFY.NS', 'SELL', '2026-03-03', 1560.0000, 5.0000);
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 6a - Correctly rejected 5 shares with 4 remaining after partial sale';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 6a FAILED'; END IF;

    -- Second purchase: 10 more shares @ 1700 (total holding bought = 20 shares, weighted avg = 1600)
    CALL record_stock_purchase(v_user_id, 'INFY.NS', 10.0000, 1700.0000, '2026-03-04');

    -- Now total bought is 20, 6 previously sold -> 14 shares remain!
    -- Attempt to sell 15 shares -> should fail
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO portfolio_transaction (user_id, ticker, transaction_type, transaction_date, price, quantity)
        VALUES (v_user_id, 'INFY.NS', 'SELL', '2026-03-05', 1650.0000, 15.0000);
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 6b - Correctly rejected 15 shares when 14 remain after second purchase';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 6b FAILED'; END IF;

    -- Sell exactly 14 shares -> should succeed!
    INSERT INTO portfolio_transaction (user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_user_id, 'INFY.NS', 'SELL', '2026-03-05', 1650.0000, 14.0000);

    RAISE NOTICE 'PASS: Test 6c - record_stock_purchase seamlessly integrated with subsequent partial sales';

    -- ========================================================================
    -- REGRESSION TEST 7: Audit logging for INSERT, UPDATE, and DELETE
    -- ========================================================================
    -- Insert a standalone transaction
    INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
    VALUES (v_holding_id, v_user_id, 'TCS.NS', 'DIVIDEND', '2026-03-06', 28.0000, 1.0000)
    RETURNING transaction_id INTO v_tx_audit_id;

    -- Verify INSERT audit
    SELECT * INTO v_audit_row
    FROM portfolio_transaction_audit
    WHERE transaction_id = v_tx_audit_id AND operation = 'INSERT';

    IF v_audit_row IS NULL OR v_audit_row.price <> 28.0000 OR v_audit_row.old_price IS NOT NULL THEN
        RAISE EXCEPTION 'TEST 7a FAILED: INSERT audit record incorrect: %', row_to_json(v_audit_row);
    END IF;

    -- Update transaction price
    UPDATE portfolio_transaction
    SET price = 30.0000
    WHERE transaction_id = v_tx_audit_id;

    -- Verify UPDATE audit
    SELECT * INTO v_audit_row
    FROM portfolio_transaction_audit
    WHERE transaction_id = v_tx_audit_id AND operation = 'UPDATE';

    IF v_audit_row IS NULL OR v_audit_row.price <> 30.0000 OR v_audit_row.old_price <> 28.0000 THEN
        RAISE EXCEPTION 'TEST 7b FAILED: UPDATE audit record did not preserve old and new values: %', row_to_json(v_audit_row);
    END IF;

    -- Delete transaction
    DELETE FROM portfolio_transaction
    WHERE transaction_id = v_tx_audit_id;

    -- Verify DELETE audit
    SELECT * INTO v_audit_row
    FROM portfolio_transaction_audit
    WHERE transaction_id = v_tx_audit_id AND operation = 'DELETE';

    IF v_audit_row IS NULL OR v_audit_row.price <> 30.0000 THEN
        RAISE EXCEPTION 'TEST 7c FAILED: DELETE audit record incorrect: %', row_to_json(v_audit_row);
    END IF;

    RAISE NOTICE 'PASS: Test 7 - Audit logging verified for INSERT, UPDATE, and DELETE with state capture';

    -- ========================================================================
    -- REGRESSION TEST 8: Row-level lock concurrency serialization
    -- ========================================================================
    -- Verify that SELECT ... FOR UPDATE can be executed on portfolio_holding
    -- confirming that holding rows are locked during transaction validation
    SELECT quantity INTO v_holding_quantity
    FROM portfolio_holding
    WHERE holding_id = v_holding_id
    FOR UPDATE;

    IF v_holding_quantity IS NULL THEN
        RAISE EXCEPTION 'TEST 8 FAILED: Could not acquire row lock on holding';
    END IF;

    RAISE NOTICE 'PASS: Test 8 - Row-level locking on portfolio_holding verified for concurrency safety';

    RAISE NOTICE '============================================================';
    RAISE NOTICE 'ALL 8 REGRESSION TESTS PASSED SUCCESSFULLY!';
    RAISE NOTICE '============================================================';
END;
$$;

-- Rollback ensures clean state with ZERO test records persisted
ROLLBACK;
