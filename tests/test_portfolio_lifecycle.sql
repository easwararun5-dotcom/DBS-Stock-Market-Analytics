-- ============================================================================
-- Test Suite: Portfolio Lifecycle & record_stock_sale Validation
-- Database:   stock_market_db (PostgreSQL 18)
-- All operations run inside an atomic transaction and are ROLLED BACK.
-- No test data is persisted to the database.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_id           INTEGER;
    v_holding_row       RECORD;
    v_val_row           RECORD;
    v_pnl_row           RECORD;
    v_audit_row         RECORD;
    v_err_caught        BOOLEAN;
    v_latest_price      NUMERIC;
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'STARTING PORTFOLIO LIFECYCLE & STOCK SALE REGRESSION SUITE';
    RAISE NOTICE '============================================================';

    -- ------------------------------------------------------------------------
    -- Setup Test Fixture: Create temporary test user
    -- ------------------------------------------------------------------------
    INSERT INTO app_user (username, email, password_hash, role)
    VALUES ('lifecycle_test_user', 'lifecycle@example.com', 'pwd_hash', 'user')
    RETURNING user_id INTO v_user_id;

    -- Fetch latest market price for TCS.NS for downstream mathematical assertion
    SELECT close_price INTO v_latest_price
    FROM daily_price_history
    WHERE ticker = 'TCS.NS'
    ORDER BY trading_date DESC
    LIMIT 1;

    RAISE NOTICE 'Fixture setup: user % | TCS.NS latest close price: %', v_user_id, v_latest_price;

    -- ========================================================================
    -- TEST 1: Initial Stock Purchase via record_stock_purchase
    -- ========================================================================
    -- Buy 10 shares @ 3500.0000 on 2026-03-01
    CALL record_stock_purchase(v_user_id, 'TCS.NS', 10.0000, 3500.0000, '2026-03-01');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    IF v_holding_row.quantity <> 10.0000 OR
       v_holding_row.invested_value <> 35000.00 OR
       v_holding_row.average_buy_price <> 3500.0000 THEN
        RAISE EXCEPTION 'TEST 1 FAILED: Initial purchase state incorrect: %', row_to_json(v_holding_row);
    END IF;

    RAISE NOTICE 'PASS: Test 1 - Initial purchase of 10 shares @ 3500 verified';

    -- ========================================================================
    -- TEST 2: Partial Stock Sale via record_stock_sale
    -- ========================================================================
    -- Sell 4 shares @ 3600.0000 on 2026-03-02
    CALL record_stock_sale(v_user_id, 'TCS.NS', 4.0000, 3600.0000, '2026-03-02');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    -- Remaining quantity: 6. Average buy price: 3500. Invested value: 6 * 3500 = 21000
    IF v_holding_row.quantity <> 6.0000 OR
       v_holding_row.average_buy_price <> 3500.0000 OR
       v_holding_row.invested_value <> 21000.00 THEN
        RAISE EXCEPTION 'TEST 2 FAILED: Partial sale holding state incorrect: %', row_to_json(v_holding_row);
    END IF;

    -- Verify transaction logged
    IF NOT EXISTS (
        SELECT 1 FROM portfolio_transaction
        WHERE user_id = v_user_id AND ticker = 'TCS.NS'
          AND transaction_type = 'SELL' AND quantity = 4.0000 AND price = 3600.0000
    ) THEN
        RAISE EXCEPTION 'TEST 2 FAILED: SELL transaction not found in ledger';
    END IF;

    -- Verify audit logged
    SELECT * INTO v_audit_row
    FROM portfolio_transaction_audit
    WHERE user_id = v_user_id AND ticker = 'TCS.NS' AND transaction_type = 'SELL'
    ORDER BY audit_id DESC LIMIT 1;

    IF v_audit_row IS NULL OR v_audit_row.operation <> 'INSERT' OR v_audit_row.quantity <> 4.0000 THEN
        RAISE EXCEPTION 'TEST 2 FAILED: Audit record for SELL missing or incorrect: %', row_to_json(v_audit_row);
    END IF;

    RAISE NOTICE 'PASS: Test 2 - Partial sale of 4 shares verified (6 remaining, cost basis: 21,000)';

    -- ========================================================================
    -- TEST 3: Valuation and Unrealised P&L after Partial Sale
    -- ========================================================================
    SELECT * INTO v_val_row
    FROM calculate_portfolio_value(v_user_id)
    WHERE ticker = 'TCS.NS';

    IF v_val_row.quantity <> 6.0000 OR
       v_val_row.market_value <> (6.0000 * v_latest_price) THEN
        RAISE EXCEPTION 'TEST 3a FAILED: Portfolio value incorrect after partial sale: %', row_to_json(v_val_row);
    END IF;

    SELECT * INTO v_pnl_row
    FROM calculate_portfolio_profit_loss(v_user_id)
    WHERE ticker = 'TCS.NS';

    IF v_pnl_row.quantity <> 6.0000 OR
       v_pnl_row.invested_value <> 21000.00 OR
       v_pnl_row.unrealised_pnl <> ((6.0000 * v_latest_price) - 21000.00) THEN
        RAISE EXCEPTION 'TEST 3b FAILED: Portfolio P&L incorrect after partial sale: %', row_to_json(v_pnl_row);
    END IF;

    RAISE NOTICE 'PASS: Test 3 - Portfolio valuation and P&L accurately report 6 remaining shares';

    -- ========================================================================
    -- TEST 4: Invalid Sales Rejections
    -- ========================================================================
    -- 4a: Non-positive quantity
    v_err_caught := FALSE;
    BEGIN
        CALL record_stock_sale(v_user_id, 'TCS.NS', 0.0000, 3600.0000, '2026-03-03');
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4a - Correctly rejected 0 quantity';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4a FAILED'; END IF;

    -- 4b: Negative price
    v_err_caught := FALSE;
    BEGIN
        CALL record_stock_sale(v_user_id, 'TCS.NS', 1.0000, -10.0000, '2026-03-03');
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4b - Correctly rejected negative price';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4b FAILED'; END IF;

    -- 4c: Stock user does not own
    v_err_caught := FALSE;
    BEGIN
        CALL record_stock_sale(v_user_id, 'INFY.NS', 1.0000, 1500.0000, '2026-03-03');
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4c - Correctly rejected selling unowned ticker';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4c FAILED'; END IF;

    -- 4d: Overselling (attempting to sell 10 shares when user owns 6)
    v_err_caught := FALSE;
    BEGIN
        CALL record_stock_sale(v_user_id, 'TCS.NS', 10.0000, 3600.0000, '2026-03-03');
    EXCEPTION
        WHEN invalid_parameter_value THEN
            v_err_caught := TRUE;
            RAISE NOTICE 'PASS: Test 4d - Correctly rejected selling 10 shares with 6 remaining';
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION 'TEST 4d FAILED'; END IF;

    -- ========================================================================
    -- TEST 5: Complete Stock Sale (Selling all remaining 6 shares)
    -- ========================================================================
    CALL record_stock_sale(v_user_id, 'TCS.NS', 6.0000, 3700.0000, '2026-03-04');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    IF v_holding_row.quantity <> 0.0000 OR
       v_holding_row.invested_value <> 0.00 OR
       v_holding_row.average_buy_price <> 0.0000 THEN
        RAISE EXCEPTION 'TEST 5 FAILED: Complete sale did not reset holding to 0: %', row_to_json(v_holding_row);
    END IF;

    -- Verify valuation excludes closed position
    IF EXISTS (
        SELECT 1 FROM calculate_portfolio_value(v_user_id) WHERE ticker = 'TCS.NS'
    ) THEN
        RAISE EXCEPTION 'TEST 5 FAILED: Closed position still returned in portfolio valuation';
    END IF;

    -- Verify P&L excludes closed position
    IF EXISTS (
        SELECT 1 FROM calculate_portfolio_profit_loss(v_user_id) WHERE ticker = 'TCS.NS'
    ) THEN
        RAISE EXCEPTION 'TEST 5 FAILED: Closed position still returned in portfolio P&L';
    END IF;

    RAISE NOTICE 'PASS: Test 5 - Complete sale verified (0 shares, excluded from active valuation & P&L)';

    -- ========================================================================
    -- TEST 6: Repeated Purchase after Complete Sale (Reactivating Position)
    -- ========================================================================
    -- Buy 5 shares @ 3800
    CALL record_stock_purchase(v_user_id, 'TCS.NS', 5.0000, 3800.0000, '2026-03-05');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    IF v_holding_row.quantity <> 5.0000 OR
       v_holding_row.average_buy_price <> 3800.0000 OR
       v_holding_row.invested_value <> 19000.00 THEN
        RAISE EXCEPTION 'TEST 6a FAILED: Reactivated holding state incorrect: %', row_to_json(v_holding_row);
    END IF;

    -- Buy 5 more shares @ 4000 (weighted avg: 3900, invested: 39000, total qty: 10)
    CALL record_stock_purchase(v_user_id, 'TCS.NS', 5.0000, 4000.0000, '2026-03-06');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    IF v_holding_row.quantity <> 10.0000 OR
       v_holding_row.average_buy_price <> 3900.0000 OR
       v_holding_row.invested_value <> 39000.00 THEN
        RAISE EXCEPTION 'TEST 6b FAILED: Averaged reactivated holding state incorrect: %', row_to_json(v_holding_row);
    END IF;

    -- Partial sale of 3 shares @ 4200 (7 remaining @ 3900, cost basis: 27300)
    CALL record_stock_sale(v_user_id, 'TCS.NS', 3.0000, 4200.0000, '2026-03-07');

    SELECT h.* INTO v_holding_row
    FROM portfolio_holding h
    JOIN user_portfolio up ON h.portfolio_id = up.portfolio_id
    WHERE up.user_id = v_user_id AND h.ticker = 'TCS.NS';

    IF v_holding_row.quantity <> 7.0000 OR
       v_holding_row.average_buy_price <> 3900.0000 OR
       v_holding_row.invested_value <> 27300.00 THEN
        RAISE EXCEPTION 'TEST 6c FAILED: Holding state after post-reactivation sale incorrect: %', row_to_json(v_holding_row);
    END IF;

    -- Check P&L on the 7 remaining shares
    SELECT * INTO v_pnl_row
    FROM calculate_portfolio_profit_loss(v_user_id)
    WHERE ticker = 'TCS.NS';

    IF v_pnl_row.quantity <> 7.0000 OR
       v_pnl_row.invested_value <> 27300.00 OR
       v_pnl_row.unrealised_pnl <> ((7.0000 * v_latest_price) - 27300.00) THEN
        RAISE EXCEPTION 'TEST 6d FAILED: Reactivated P&L incorrect: %', row_to_json(v_pnl_row);
    END IF;

    RAISE NOTICE 'PASS: Test 6 - Reactivation after complete sale and subsequent averaging & sale verified';

    RAISE NOTICE '============================================================';
    RAISE NOTICE 'ALL PORTFOLIO LIFECYCLE TESTS PASSED SUCCESSFULLY!';
    RAISE NOTICE '============================================================';
END;
$$;

ROLLBACK;
