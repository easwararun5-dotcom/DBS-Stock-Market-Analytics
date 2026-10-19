-- ============================================================================
-- Trigger:  trg_portfolio_transaction_audit
-- Table:    portfolio_transaction
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================
-- Purpose:
--   Maintains an immutable audit ledger of all INSERT, UPDATE, and DELETE
--   operations executed against portfolio_transaction.
--
-- Audit Table: portfolio_transaction_audit
--   - Captures operation type ('INSERT', 'UPDATE', 'DELETE')
--   - Preserves complete transaction record attributes (transaction_id, holding_id,
--     user_id, ticker, transaction_type, transaction_date, price, quantity)
--   - For UPDATE events, records prior price and prior quantity (old_price, old_quantity)
--   - Captures audit timestamp (CURRENT_TIMESTAMP) and database user (CURRENT_USER)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create Audit Table
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_transaction_audit (
    audit_id SERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    transaction_id INTEGER NOT NULL,
    holding_id INTEGER,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    price NUMERIC(14,4) NOT NULL,
    quantity NUMERIC(20,4) NOT NULL,
    old_price NUMERIC(14,4),
    old_quantity NUMERIC(20,4),
    audit_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    audit_user TEXT NOT NULL DEFAULT CURRENT_USER
);

COMMENT ON TABLE portfolio_transaction_audit IS 
'Immutable audit ledger recording all mutations (INSERT, UPDATE, DELETE) on portfolio_transaction.';

CREATE INDEX IF NOT EXISTS idx_audit_transaction_id ON portfolio_transaction_audit(transaction_id);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON portfolio_transaction_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON portfolio_transaction_audit(audit_timestamp);

-- ----------------------------------------------------------------------------
-- 2. Audit Trigger Function
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_portfolio_transaction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO portfolio_transaction_audit (
            operation,
            transaction_id,
            holding_id,
            user_id,
            ticker,
            transaction_type,
            transaction_date,
            price,
            quantity,
            old_price,
            old_quantity,
            audit_timestamp,
            audit_user
        ) VALUES (
            'INSERT',
            NEW.transaction_id,
            NEW.holding_id,
            NEW.user_id,
            NEW.ticker,
            NEW.transaction_type,
            NEW.transaction_date,
            NEW.price,
            NEW.quantity,
            NULL,
            NULL,
            CURRENT_TIMESTAMP,
            CURRENT_USER
        );
        RETURN NEW;

    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO portfolio_transaction_audit (
            operation,
            transaction_id,
            holding_id,
            user_id,
            ticker,
            transaction_type,
            transaction_date,
            price,
            quantity,
            old_price,
            old_quantity,
            audit_timestamp,
            audit_user
        ) VALUES (
            'UPDATE',
            NEW.transaction_id,
            NEW.holding_id,
            NEW.user_id,
            NEW.ticker,
            NEW.transaction_type,
            NEW.transaction_date,
            NEW.price,
            NEW.quantity,
            OLD.price,
            OLD.quantity,
            CURRENT_TIMESTAMP,
            CURRENT_USER
        );
        RETURN NEW;

    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO portfolio_transaction_audit (
            operation,
            transaction_id,
            holding_id,
            user_id,
            ticker,
            transaction_type,
            transaction_date,
            price,
            quantity,
            old_price,
            old_quantity,
            audit_timestamp,
            audit_user
        ) VALUES (
            'DELETE',
            OLD.transaction_id,
            OLD.holding_id,
            OLD.user_id,
            OLD.ticker,
            OLD.transaction_type,
            OLD.transaction_date,
            OLD.price,
            OLD.quantity,
            OLD.price,
            OLD.quantity,
            CURRENT_TIMESTAMP,
            CURRENT_USER
        );
        RETURN OLD;
    END IF;

    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION fn_audit_portfolio_transaction() IS
'Trigger function recording INSERT, UPDATE, and DELETE operations on portfolio_transaction into portfolio_transaction_audit.';

-- ----------------------------------------------------------------------------
-- 3. Trigger Definition
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_portfolio_transaction_audit ON portfolio_transaction;

CREATE TRIGGER trg_portfolio_transaction_audit
AFTER INSERT OR UPDATE OR DELETE ON portfolio_transaction
FOR EACH ROW
EXECUTE FUNCTION fn_audit_portfolio_transaction();
