-- ============================================================================
-- 01_basic_queries.sql
-- Description: Basic SELECT, WHERE, ORDER BY, and LIMIT queries
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 1.1: Top 10 Largest Companies by Market Capitalization
-- Demonstrates: Column selection, ORDER BY DESC, LIMIT
-- Business Purpose: Identify the mega-cap market leaders driving the Nifty 50 index.
SELECT 
    ticker,
    company_name,
    sector_id
FROM company
ORDER BY ticker ASC
LIMIT 10;

-- Query 1.2: Filter Companies by Valuation Multiples (P/E < 25 and Forward P/E < 20)
-- Demonstrates: Multi-condition WHERE clause with AND, numeric comparisons, ORDER BY
-- Business Purpose: Screen for potentially undervalued or value-oriented equities.
SELECT 
    ticker,
    pe_ratio,
    forward_pe,
    price_to_book,
    dividend_yield,
    market_cap
FROM current_fundamentals
WHERE pe_ratio IS NOT NULL 
  AND pe_ratio < 25.0
  AND forward_pe < 20.0
ORDER BY pe_ratio ASC
LIMIT 10;

-- Query 1.3: Companies with Multiple Stock Splits
-- Demonstrates: Filter on integer count, sorting descending with secondary sort
-- Business Purpose: Identify high-growth companies that frequently split shares to maintain retail liquidity.
SELECT 
    ticker,
    total_trading_days,
    number_of_splits,
    total_dividends_paid,
    total_return_pct
FROM stock_summary
WHERE number_of_splits >= 3
ORDER BY number_of_splits DESC, total_return_pct DESC;

-- Query 1.4: Recent Trading History for a Benchmark Heavyweight (RELIANCE.NS)
-- Demonstrates: Filtering by ticker natural key and date, ORDER BY date DESC, LIMIT
-- Business Purpose: Retrieve the latest pricing and moving averages for technical analysis.
SELECT 
    ticker,
    trading_date,
    open_price,
    high_price,
    low_price,
    close_price,
    volume,
    ma_50,
    ma_200
FROM daily_price_history
WHERE ticker = 'RELIANCE.NS'
ORDER BY trading_date DESC
LIMIT 10;

-- Query 1.5: High-Liquidity Stocks by Average Daily Volume
-- Demonstrates: Filtering numeric thresholds (> 5,000,000 shares/day), formatted display
-- Business Purpose: Screen for highly liquid instruments suitable for institutional block trades.
SELECT 
    ticker,
    avg_daily_volume,
    current_market_cap,
    volatility_pct
FROM stock_summary
WHERE avg_daily_volume >= 5000000
ORDER BY avg_daily_volume DESC
LIMIT 10;
