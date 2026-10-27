-- ============================================================================
-- Migration: 04_auth_and_user_portfolios.sql
-- Database: stock_market_db (PostgreSQL port 5435)
-- Description: Adds user_portfolio table, full_name in app_user, and portfolio foreign keys
-- ============================================================================

-- 1. Extend app_user with full_name
ALTER TABLE app_user 
ADD COLUMN IF NOT EXISTS full_name TEXT;

-- 2. Create user_portfolio table
CREATE TABLE IF NOT EXISTS user_portfolio (
    portfolio_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    portfolio_name TEXT NOT NULL DEFAULT 'Main Portfolio',
    description TEXT,
    cash_balance NUMERIC(22,2) NOT NULL DEFAULT 100000.00 CHECK (cash_balance >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_portfolio_name UNIQUE (user_id, portfolio_name)
);

-- 3. Link portfolio_holding to user_portfolio
ALTER TABLE portfolio_holding 
ADD COLUMN IF NOT EXISTS portfolio_id INT REFERENCES user_portfolio(portfolio_id) ON DELETE CASCADE;

-- 4. Link portfolio_transaction to user_portfolio
ALTER TABLE portfolio_transaction 
ADD COLUMN IF NOT EXISTS portfolio_id INT REFERENCES user_portfolio(portfolio_id) ON DELETE CASCADE;

-- 5. Performance and Integrity Indexes
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_portfolio_id ON portfolio_holding(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_user_id ON portfolio_holding(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_ticker ON portfolio_holding(ticker);
CREATE INDEX IF NOT EXISTS idx_portfolio_transaction_portfolio_id ON portfolio_transaction(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_transaction_user_id ON portfolio_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_user_id ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_ticker ON user_watchlist(ticker);
