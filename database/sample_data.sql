-- ============================================================================
-- Project: DBS – Stock Market Analytics and Portfolio Management System
-- Database: stock_market_db (PostgreSQL 17/18)
-- Description: Representative Sample Data Seed File
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. SECTOR SAMPLE DATA (13 Economic Sectors)
-- ----------------------------------------------------------------------------
INSERT INTO sector (sector_id, sector_name) VALUES
    (1, 'Information Technology'),
    (2, 'Financial Services'),
    (3, 'Oil & Gas'),
    (4, 'Automobile'),
    (5, 'Healthcare'),
    (6, 'Fast Moving Consumer Goods'),
    (7, 'Metals & Mining'),
    (8, 'Construction Materials'),
    (9, 'Consumer Durables'),
    (10, 'Power'),
    (11, 'Telecommunications'),
    (12, 'Services'),
    (13, 'Chemicals')
ON CONFLICT (sector_id) DO UPDATE SET sector_name = EXCLUDED.sector_name;

SELECT setval(pg_get_serial_sequence('sector', 'sector_id'), (SELECT MAX(sector_id) FROM sector));

-- ----------------------------------------------------------------------------
-- 2. COMPANY SAMPLE DATA (Representative Indian Blue-Chips)
-- ----------------------------------------------------------------------------
INSERT INTO company (ticker, company_name, sector_id) VALUES
    ('RELIANCE.NS', 'Reliance Industries Limited', 3),
    ('TCS.NS', 'Tata Consultancy Services Limited', 1),
    ('INFY.NS', 'Infosys Limited', 1),
    ('HDFCBANK.NS', 'HDFC Bank Limited', 2),
    ('ICICIBANK.NS', 'ICICI Bank Limited', 2),
    ('ADANIENT.NS', 'Adani Enterprises Limited', 12),
    ('BHARTIARTL.NS', 'Bharti Airtel Limited', 11),
    ('ITC.NS', 'ITC Limited', 6),
    ('TATAMOTORS.NS', 'Tata Motors Limited', 4),
    ('SUNPHARMA.NS', 'Sun Pharmaceutical Industries Limited', 5),
    ('TATASTEEL.NS', 'Tata Steel Limited', 7),
    ('NTPC.NS', 'NTPC Limited', 10),
    ('ULTRACEMCO.NS', 'UltraTech Cement Limited', 8),
    ('TITAN.NS', 'Titan Company Limited', 9),
    ('PIDILITIND.NS', 'Pidilite Industries Limited', 13)
ON CONFLICT (ticker) DO UPDATE SET 
    company_name = EXCLUDED.company_name,
    sector_id = EXCLUDED.sector_id;

-- ----------------------------------------------------------------------------
-- 3. CURRENT FUNDAMENTALS SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO current_fundamentals (ticker, pe_ratio, forward_pe, price_to_book, dividend_yield, eps, beta, fiscal_year, market_cap, peg_ratio, last_updated) VALUES
    ('RELIANCE.NS', 24.85, 21.30, 2.45, 0.38, 105.20, 1.05, 2026, 1785000000000.00, 1.45, '2026-01-30'),
    ('TCS.NS', 28.40, 25.10, 12.10, 1.35, 138.50, 0.78, 2026, 1420000000000.00, 2.10, '2026-01-30'),
    ('INFY.NS', 24.10, 22.00, 7.80, 2.10, 78.40, 0.95, 2026, 780000000000.00, 1.65, '2026-01-30'),
    ('HDFCBANK.NS', 18.20, 16.50, 2.80, 1.15, 92.10, 0.85, 2026, 1280000000000.00, 1.20, '2026-01-30'),
    ('ICICIBANK.NS', 17.50, 15.20, 3.10, 0.95, 72.80, 1.12, 2026, 890000000000.00, 1.10, '2026-01-30'),
    ('ADANIENT.NS', 45.60, 38.20, 5.40, 0.05, 44.30, 1.85, 2026, 230000000000.00, 3.20, '2026-01-30'),
    ('BHARTIARTL.NS', 32.10, 26.40, 6.20, 0.70, 48.20, 0.90, 2026, 910000000000.00, 1.50, '2026-01-30'),
    ('ITC.NS', 26.30, 24.00, 7.40, 3.20, 18.10, 0.65, 2026, 560000000000.00, 1.80, '2026-01-30')
ON CONFLICT (ticker) DO UPDATE SET
    pe_ratio = EXCLUDED.pe_ratio,
    market_cap = EXCLUDED.market_cap,
    last_updated = EXCLUDED.last_updated;

-- ----------------------------------------------------------------------------
-- 4. STOCK SUMMARY SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO stock_summary (ticker, first_trading_date, last_trading_date, total_trading_days, starting_price, ending_price, total_return_pct, highest_price, lowest_price, avg_daily_volume, total_dividends_paid, number_of_splits, avg_daily_return_pct, volatility_pct, current_market_cap, current_pe_ratio) VALUES
    ('RELIANCE.NS', '2000-01-03', '2026-01-30', 6480, 52.30, 2615.40, 4900.76, 3217.90, 45.10, 7540200, 185.50, 2, 0.0825, 24.50, 1785000000000.00, 24.85),
    ('TCS.NS', '2004-08-25', '2026-01-30', 5320, 120.50, 3935.10, 3165.64, 4592.25, 110.20, 2341500, 640.00, 3, 0.0712, 19.80, 1420000000000.00, 28.40),
    ('INFY.NS', '2000-01-03', '2026-01-30', 6480, 45.20, 1888.75, 4078.65, 1953.90, 38.40, 5210300, 412.00, 4, 0.0789, 23.10, 780000000000.00, 24.10),
    ('ADANIENT.NS', '2002-06-04', '2026-01-30', 5858, 1.25, 2020.40, 161532.00, 4190.00, 0.85, 4120800, 45.00, 1, 0.1450, 48.20, 230000000000.00, 45.60)
ON CONFLICT (ticker) DO UPDATE SET
    total_trading_days = EXCLUDED.total_trading_days,
    ending_price = EXCLUDED.ending_price;

-- ----------------------------------------------------------------------------
-- 5. CORPORATE ACTIONS SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO corporate_action (ticker, action_date, action_type, action_value) VALUES
    ('RELIANCE.NS', '2017-09-07', 'Stock_Split', 2.0000),
    ('RELIANCE.NS', '2024-10-28', 'Stock_Split', 2.0000),
    ('RELIANCE.NS', '2025-08-19', 'Dividend', 10.0000),
    ('TCS.NS', '2018-06-01', 'Stock_Split', 2.0000),
    ('TCS.NS', '2025-01-17', 'Dividend', 28.0000),
    ('INFY.NS', '2018-09-04', 'Stock_Split', 2.0000),
    ('INFY.NS', '2025-10-24', 'Dividend', 18.5000)
ON CONFLICT (ticker, action_date, action_type) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 6. APP_USER & USER_PORTFOLIO SAMPLE DATA
-- ----------------------------------------------------------------------------
-- Default demo user (password: DemoUser#2026 hashed with bcrypt)
INSERT INTO app_user (user_id, username, email, password_hash, role, full_name) VALUES
    (1, 'demo_investor', 'investor@stockmarket.internal', '$2b$12$K1f.R0gC8YIeGkWg5u8zfeB9QJ8ZfW8uG6mF7sB7YvD3iGvJ2yQ7a', 'user', 'Demo Investor')
ON CONFLICT (user_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('app_user', 'user_id'), (SELECT COALESCE(MAX(user_id), 1) FROM app_user));

INSERT INTO user_portfolio (portfolio_id, user_id, portfolio_name, description, cash_balance) VALUES
    (1, 1, 'Main Portfolio', 'Long-term diversified equity portfolio', 85000.00)
ON CONFLICT (user_id, portfolio_name) DO NOTHING;

SELECT setval(pg_get_serial_sequence('user_portfolio', 'portfolio_id'), (SELECT COALESCE(MAX(portfolio_id), 1) FROM user_portfolio));

-- ----------------------------------------------------------------------------
-- 7. PORTFOLIO_HOLDING & PORTFOLIO_TRANSACTION SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO portfolio_holding (holding_id, portfolio_id, ticker, quantity, invested_value, average_buy_price, purchase_date) VALUES
    (1, 1, 'RELIANCE.NS', 10.0000, 25500.00, 2550.0000, '2026-01-15'),
    (2, 1, 'TCS.NS', 5.0000, 19200.00, 3840.0000, '2026-01-20')
ON CONFLICT (portfolio_id, ticker) DO NOTHING;

SELECT setval(pg_get_serial_sequence('portfolio_holding', 'holding_id'), (SELECT COALESCE(MAX(holding_id), 2) FROM portfolio_holding));

INSERT INTO portfolio_transaction (portfolio_id, holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity) VALUES
    (1, 1, 1, 'RELIANCE.NS', 'BUY', '2026-01-15', 2550.0000, 10.0000),
    (1, 2, 1, 'TCS.NS', 'BUY', '2026-01-20', 3840.0000, 5.0000)
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------------------------
-- 8. USER_WATCHLIST SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO user_watchlist (watchlist_id, user_id, ticker, alert_price) VALUES
    (1, 1, 'INFY.NS', 1850.0000),
    (2, 1, 'HDFCBANK.NS', 1600.0000)
ON CONFLICT (user_id, ticker) DO NOTHING;

SELECT setval(pg_get_serial_sequence('user_watchlist', 'watchlist_id'), (SELECT COALESCE(MAX(watchlist_id), 2) FROM user_watchlist));

-- ----------------------------------------------------------------------------
-- 9. ML_PREDICTION SAMPLE DATA
-- ----------------------------------------------------------------------------
INSERT INTO ml_prediction (ticker, prediction_date, forecast_horizon, predicted_price, confidence_score, model_name) VALUES
    ('RELIANCE.NS', '2026-01-30', 5, 2680.5000, 0.7250, 'HistGradientBoosting_Classifier_v1'),
    ('TCS.NS', '2026-01-30', 5, 4015.0000, 0.6890, 'HistGradientBoosting_Classifier_v1'),
    ('ADANIENT.NS', '2026-01-30', 5, 2095.0000, 0.6420, 'HistGradientBoosting_Classifier_v1')
ON CONFLICT DO NOTHING;

COMMIT;

