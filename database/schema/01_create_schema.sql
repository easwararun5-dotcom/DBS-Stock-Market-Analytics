-- ============================================================================
-- Project: DBS – Stock Market Analytics and Portfolio Management System
-- Database: stock_market_db (PostgreSQL 18.4)
-- Description: DDL Migration Script for all 13 Tables and Supporting Indexes
-- Status: Pre-Implementation Audited Specification (NOT YET EXECUTED)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. SECTOR
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name TEXT NOT NULL UNIQUE
);

COMMENT ON TABLE sector IS 'Industry classification for companies (ER Diagram Sheet 3). Exactly 13 distinct sectors verified from datasets.';

-- ----------------------------------------------------------------------------
-- 2. COMPANY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector_id INT NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT
);

COMMENT ON TABLE company IS 'Core company registry identified by stock ticker symbol (ER Diagram Sheet 1 & 3). Exactly 49 companies verified across both datasets. Note: listing_date and exchange omitted per ER diagram fidelity.';

-- ----------------------------------------------------------------------------
-- 3. DAILY_PRICE_HISTORY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_price_history (
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    trading_date DATE NOT NULL,
    open_price NUMERIC(14,4),
    high_price NUMERIC(14,4),
    low_price NUMERIC(14,4),
    close_price NUMERIC(14,4),
    volume BIGINT CHECK (volume >= 0),
    -- Dataset-derived analytical extensions (approved):
    daily_return NUMERIC(10,4),
    vol_20d NUMERIC(10,4),
    ma_50 NUMERIC(14,4),
    ma_200 NUMERIC(14,4),
    PRIMARY KEY (ticker, trading_date)
);

COMMENT ON TABLE daily_price_history IS 'Daily historical price records and analytical technical indicators (ER Diagram Sheet 1 & 3). Note: Price columns omit >= 0 checks to support backwards-adjusted historical prices (e.g. ADANIENT.NS 2002 corporate dividend adjustment).';

-- ----------------------------------------------------------------------------
-- 4. CORPORATE_ACTION
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS corporate_action (
    action_id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    action_date DATE NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('Dividend', 'Stock_Split')),
    action_value NUMERIC(14,4) NOT NULL CHECK (action_value > 0),
    CONSTRAINT uq_corp_action UNIQUE (ticker, action_date, action_type)
);

COMMENT ON TABLE corporate_action IS 'Corporate action events (dividends and stock splits) extracted from historical data (ER Diagram Sheet 1 & 3). Unique constraint prevents duplicate events while allowing both a dividend and a split on the same date.';

-- ----------------------------------------------------------------------------
-- 5. CURRENT_FUNDAMENTALS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS current_fundamentals (
    ticker TEXT PRIMARY KEY REFERENCES company(ticker) ON DELETE CASCADE,
    pe_ratio NUMERIC(10,4),
    forward_pe NUMERIC(10,4),
    price_to_book NUMERIC(10,4),
    dividend_yield NUMERIC(10,4),
    eps NUMERIC(14,4),
    beta NUMERIC(10,4),
    fiscal_year INT,  -- Derived snapshot year from latest available date (2026)
    -- Dataset-derived analytical extensions (approved):
    market_cap NUMERIC(22,2),
    peg_ratio NUMERIC(10,4),
    last_updated DATE NOT NULL DEFAULT CURRENT_DATE
);

COMMENT ON TABLE current_fundamentals IS 'Latest fundamentals snapshot per company (ER Diagram Sheet 1 & 3). Uniform snapshot date 2026-01-30 across all 49 tickers. Note: fiscal_year represents derived snapshot year; market_cap and peg_ratio are retained dataset extensions; missing source metrics ingested as NULL.';

-- ----------------------------------------------------------------------------
-- 6. STOCK_SUMMARY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_summary (
    ticker TEXT PRIMARY KEY REFERENCES company(ticker) ON DELETE CASCADE,
    first_trading_date DATE NOT NULL,
    last_trading_date DATE NOT NULL,
    total_trading_days INT NOT NULL CHECK (total_trading_days > 0),
    starting_price NUMERIC(16,4),
    ending_price NUMERIC(16,4),
    total_return_pct NUMERIC(18,4),
    highest_price NUMERIC(16,4),
    lowest_price NUMERIC(16,4),
    avg_daily_volume NUMERIC(18,2),
    total_dividends_paid NUMERIC(16,4),
    number_of_splits INT NOT NULL DEFAULT 0 CHECK (number_of_splits >= 0),
    avg_daily_return_pct NUMERIC(10,4),
    volatility_pct NUMERIC(10,4),
    current_market_cap NUMERIC(22,2),
    current_pe_ratio NUMERIC(10,4)
);

COMMENT ON TABLE stock_summary IS 'Long-term historical aggregate metrics per company from nifty50_summary_statistics.csv (ER Diagram Sheet 1). Exactly 49 records.';

-- ----------------------------------------------------------------------------
-- 7. APP_USER
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_user (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE app_user IS 'Application user authentication and role management (ER Diagram Sheet 2).';

-- ----------------------------------------------------------------------------
-- 8. USER_WATCHLIST
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_watchlist (
    watchlist_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    alert_price NUMERIC(14,4),
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_ticker UNIQUE (user_id, ticker)
);

COMMENT ON TABLE user_watchlist IS 'User watchlist items tracking target price alerts (ER Diagram Sheet 2).';

-- ----------------------------------------------------------------------------
-- 9. PORTFOLIO_HOLDING
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_holding (
    holding_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE RESTRICT,
    quantity NUMERIC(20,4) NOT NULL CHECK (quantity >= 0),
    invested_value NUMERIC(22,2) NOT NULL CHECK (invested_value >= 0),
    average_buy_price NUMERIC(14,4) NOT NULL CHECK (average_buy_price >= 0),
    purchase_date DATE NOT NULL,
    CONSTRAINT uq_holding_user UNIQUE (holding_id, user_id)
);

COMMENT ON TABLE portfolio_holding IS 'Aggregated user investment positions (ER Diagram Sheet 2). Unique constraint on (holding_id, user_id) enforces cross-table ownership validation.';

-- ----------------------------------------------------------------------------
-- 10. PORTFOLIO_TRANSACTION
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_transaction (
    transaction_id SERIAL PRIMARY KEY,
    holding_id INT,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE RESTRICT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL', 'DIVIDEND', 'SPLIT')),
    transaction_date DATE NOT NULL,
    price NUMERIC(14,4) NOT NULL CHECK (price >= 0),
    quantity NUMERIC(20,4) NOT NULL CHECK (quantity > 0),
    CONSTRAINT fk_transaction_holding_user FOREIGN KEY (holding_id, user_id)
        REFERENCES portfolio_holding(holding_id, user_id) ON DELETE SET NULL (holding_id)
);

COMMENT ON TABLE portfolio_transaction IS 'Detailed ledger of user trading activity (ER Diagram Sheet 2). Composite foreign key (holding_id, user_id) with ON DELETE SET NULL (holding_id) prevents transactions from referencing a holding owned by a different user while preserving user_id when a holding is deleted.';

-- ----------------------------------------------------------------------------
-- 11. ALERT
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert (
    alert_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,
    alert_message TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'READ', 'DISMISSED')),
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE alert IS 'System and price threshold notifications generated by companies and received by users (ER Diagram Sheet 2).';

-- ----------------------------------------------------------------------------
-- 12. PORTFOLIO_RISK_ANALYSIS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_risk_analysis (
    analysis_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL DEFAULT CURRENT_DATE,
    sharpe_ratio NUMERIC(10,4),
    volatility NUMERIC(10,4),
    max_drawdown NUMERIC(10,4),
    sector_concentration JSONB,
    transaction_context TEXT  -- Diagram attribute oval "transaction" (no FK)
);

COMMENT ON TABLE portfolio_risk_analysis IS 'Computed risk metrics and portfolio concentrations for users (ER Diagram Sheet 2).';

-- ----------------------------------------------------------------------------
-- 13. ML_PREDICTION
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ml_prediction (
    prediction_id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    prediction_date DATE NOT NULL,
    forecast_horizon INT NOT NULL CHECK (forecast_horizon > 0),
    predicted_price NUMERIC(14,4) NOT NULL,
    confidence_score NUMERIC(6,4) CHECK (confidence_score BETWEEN 0 AND 1),
    model_name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ml_prediction IS 'Machine learning forecasts generated for listed tickers (ER Diagram Sheet 1).';

-- ============================================================================
-- INDEXES (Explicit Foreign Key & High-Frequency Filter Indexes)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_company_sector_id ON company(sector_id);
CREATE INDEX IF NOT EXISTS idx_price_ticker ON daily_price_history(ticker);
CREATE INDEX IF NOT EXISTS idx_price_date ON daily_price_history(trading_date);
CREATE INDEX IF NOT EXISTS idx_corp_action_ticker ON corporate_action(ticker);
CREATE INDEX IF NOT EXISTS idx_corp_action_date ON corporate_action(action_date);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON user_watchlist(ticker);
CREATE INDEX IF NOT EXISTS idx_holding_user ON portfolio_holding(user_id);
CREATE INDEX IF NOT EXISTS idx_holding_ticker ON portfolio_holding(ticker);
CREATE INDEX IF NOT EXISTS idx_transaction_holding_user ON portfolio_transaction(holding_id, user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_user ON portfolio_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_transaction_ticker ON portfolio_transaction(ticker);
CREATE INDEX IF NOT EXISTS idx_alert_user ON alert(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_ticker ON alert(ticker);
CREATE INDEX IF NOT EXISTS idx_risk_user ON portfolio_risk_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_prediction_ticker ON ml_prediction(ticker);

COMMIT;
