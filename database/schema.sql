-- ============================================================================
-- Project: DBS – Stock Market Analytics and Portfolio Management System
-- Database: stock_market_db (PostgreSQL 17/18) & stock_timescale_db (TimescaleDB)
-- Description: Master DDL Schema Definition File
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. SECTOR
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name TEXT NOT NULL UNIQUE
);

COMMENT ON TABLE sector IS 'Industry classification for companies. 13 distinct economic sectors.';

-- ----------------------------------------------------------------------------
-- 2. COMPANY
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector_id INT NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT
);

COMMENT ON TABLE company IS 'Core company registry identified by stock ticker symbol (49 Nifty 50 companies).';

-- ----------------------------------------------------------------------------
-- 3. DAILY_PRICE_HISTORY (Relational Snapshot & TimescaleDB Hypertable)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_price_history (
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    trading_date DATE NOT NULL,
    open_price NUMERIC(14,4),
    high_price NUMERIC(14,4),
    low_price NUMERIC(14,4),
    close_price NUMERIC(14,4),
    volume BIGINT CHECK (volume >= 0),
    daily_return NUMERIC(10,4),
    vol_20d NUMERIC(10,4),
    ma_50 NUMERIC(14,4),
    ma_200 NUMERIC(14,4),
    PRIMARY KEY (ticker, trading_date)
);

COMMENT ON TABLE daily_price_history IS 'Daily historical price records and analytical technical indicators (over 287,000 records). In TimescaleDB, converted to a hypertable partitioned by trading_date (360-day chunks).';

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

COMMENT ON TABLE corporate_action IS 'Corporate action events (dividends and stock splits) extracted from historical data.';

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
    fiscal_year INT,
    market_cap NUMERIC(22,2),
    peg_ratio NUMERIC(10,4),
    last_updated DATE NOT NULL DEFAULT CURRENT_DATE
);

COMMENT ON TABLE current_fundamentals IS 'Latest fundamentals snapshot per listed company.';

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

COMMENT ON TABLE stock_summary IS 'Long-term historical aggregate metrics per company from summary statistics.';

-- ----------------------------------------------------------------------------
-- 7. APP_USER
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_user (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    full_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE app_user IS 'Application user authentication and role management (bcrypt passwords + JWT).';

-- ----------------------------------------------------------------------------
-- 8. USER_PORTFOLIO
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_portfolio (
    portfolio_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    portfolio_name TEXT NOT NULL DEFAULT 'Main Portfolio',
    description TEXT,
    cash_balance NUMERIC(22,2) NOT NULL DEFAULT 100000.00 CHECK (cash_balance >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_portfolio_name UNIQUE (user_id, portfolio_name)
);

COMMENT ON TABLE user_portfolio IS 'User portfolio instance tracking cash balance and holdings.';

-- ----------------------------------------------------------------------------
-- 9. PORTFOLIO_HOLDING (Pure 3NF)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_holding (
    holding_id SERIAL PRIMARY KEY,
    portfolio_id INT NOT NULL REFERENCES user_portfolio(portfolio_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE RESTRICT,
    quantity NUMERIC(20,4) NOT NULL CHECK (quantity >= 0),
    invested_value NUMERIC(22,2) NOT NULL CHECK (invested_value >= 0),
    average_buy_price NUMERIC(14,4) NOT NULL CHECK (average_buy_price >= 0),
    purchase_date DATE NOT NULL,
    CONSTRAINT uq_portfolio_ticker UNIQUE (portfolio_id, ticker)
);

COMMENT ON TABLE portfolio_holding IS 'Aggregated user investment positions adhering to 3NF without transitive user_id dependency.';

-- ----------------------------------------------------------------------------
-- 10. PORTFOLIO_TRANSACTION (Ledger Table)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_transaction (
    transaction_id SERIAL PRIMARY KEY,
    portfolio_id INT NOT NULL REFERENCES user_portfolio(portfolio_id) ON DELETE CASCADE,
    holding_id INT,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE RESTRICT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL', 'DIVIDEND', 'SPLIT')),
    transaction_date DATE NOT NULL,
    price NUMERIC(14,4) NOT NULL CHECK (price >= 0),
    quantity NUMERIC(20,4) NOT NULL CHECK (quantity > 0),
    CONSTRAINT fk_transaction_holding FOREIGN KEY (holding_id)
        REFERENCES portfolio_holding(holding_id) ON DELETE SET NULL
);

COMMENT ON TABLE portfolio_transaction IS 'Immutable audit ledger of user trading activity.';

-- ----------------------------------------------------------------------------
-- 11. USER_WATCHLIST
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_watchlist (
    watchlist_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    alert_price NUMERIC(14,4),
    added_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_ticker UNIQUE (user_id, ticker)
);

COMMENT ON TABLE user_watchlist IS 'User watchlist items tracking target price alerts.';

-- ----------------------------------------------------------------------------
-- 12. ALERT
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

COMMENT ON TABLE alert IS 'System and price threshold notifications generated by companies and received by users.';

-- ----------------------------------------------------------------------------
-- 13. PORTFOLIO_RISK_ANALYSIS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_risk_analysis (
    analysis_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL DEFAULT CURRENT_DATE,
    sharpe_ratio NUMERIC(10,4),
    volatility NUMERIC(10,4),
    max_drawdown NUMERIC(10,4),
    transaction_context TEXT
);

COMMENT ON TABLE portfolio_risk_analysis IS 'Computed portfolio risk metrics for users.';

-- ----------------------------------------------------------------------------
-- 14. PORTFOLIO_RISK_SECTOR_ALLOCATION (Normalized 1NF Child Table)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS portfolio_risk_sector_allocation (
    analysis_id INTEGER NOT NULL REFERENCES portfolio_risk_analysis(analysis_id) ON DELETE CASCADE,
    sector_id INTEGER NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT,
    concentration_pct NUMERIC(5,2) NOT NULL CHECK (concentration_pct >= 0 AND concentration_pct <= 100),
    CONSTRAINT pk_portfolio_risk_sector_allocation PRIMARY KEY (analysis_id, sector_id)
);

COMMENT ON TABLE portfolio_risk_sector_allocation IS 'Normalized 1NF child table representing per-sector asset allocation percentages.';

-- ----------------------------------------------------------------------------
-- 15. ML_PREDICTION
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

COMMENT ON TABLE ml_prediction IS 'Machine learning forecasts generated for listed tickers.';

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_company_sector_id ON company(sector_id);
CREATE INDEX IF NOT EXISTS idx_price_ticker ON daily_price_history(ticker);
CREATE INDEX IF NOT EXISTS idx_price_date ON daily_price_history(trading_date);
CREATE INDEX IF NOT EXISTS idx_corp_action_ticker ON corporate_action(ticker);
CREATE INDEX IF NOT EXISTS idx_corp_action_date ON corporate_action(action_date);
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_portfolio_id ON portfolio_holding(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_holding_ticker ON portfolio_holding(ticker);
CREATE INDEX IF NOT EXISTS idx_portfolio_transaction_portfolio_id ON portfolio_transaction(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_transaction_user_id ON portfolio_transaction(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_transaction_ticker ON portfolio_transaction(ticker);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON user_watchlist(ticker);
CREATE INDEX IF NOT EXISTS idx_alert_user ON alert(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_ticker ON alert(ticker);
CREATE INDEX IF NOT EXISTS idx_risk_user ON portfolio_risk_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_risk_sector_alloc_sector ON portfolio_risk_sector_allocation(sector_id);
CREATE INDEX IF NOT EXISTS idx_prediction_ticker ON ml_prediction(ticker);

-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- View 1: Latest Stock Prices
CREATE OR REPLACE VIEW v_latest_stock_prices AS
SELECT DISTINCT ON (d.ticker)
    d.ticker,
    c.company_name,
    s.sector_name,
    d.trading_date,
    d.open_price,
    d.high_price,
    d.low_price,
    d.close_price,
    d.volume,
    d.daily_return,
    d.ma_50,
    d.ma_200
FROM daily_price_history d
JOIN company c ON d.ticker = c.ticker
JOIN sector s ON c.sector_id = s.sector_id
ORDER BY d.ticker, d.trading_date DESC;

-- View 2: Company Fundamentals
CREATE OR REPLACE VIEW v_company_fundamentals AS
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    f.pe_ratio,
    f.forward_pe,
    f.price_to_book,
    f.dividend_yield,
    f.eps,
    f.beta,
    f.market_cap,
    f.peg_ratio,
    f.last_updated
FROM company c
JOIN sector s ON c.sector_id = s.sector_id
LEFT JOIN current_fundamentals f ON c.ticker = f.ticker;

-- View 3: Sector Performance
CREATE OR REPLACE VIEW v_sector_performance AS
SELECT 
    s.sector_name,
    COUNT(DISTINCT c.ticker) AS total_companies,
    ROUND(AVG(d.daily_return), 4) AS avg_sector_return,
    ROUND(AVG(f.pe_ratio), 2) AS avg_pe_ratio,
    SUM(f.market_cap) AS total_market_cap
FROM sector s
JOIN company c ON s.sector_id = c.sector_id
LEFT JOIN v_latest_stock_prices d ON c.ticker = d.ticker
LEFT JOIN current_fundamentals f ON c.ticker = f.ticker
GROUP BY s.sector_name;

COMMIT;

