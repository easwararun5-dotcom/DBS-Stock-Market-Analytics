-- ============================================================================
-- 07_stock_performance.sql
-- Description: Stock performance comparisons, risk-adjusted returns, and benchmark evaluations
-- Database: stock_market_db (PostgreSQL 18)
-- ============================================================================

-- Query 7.1: Top 10 Long-Term Wealth Compounders
-- Demonstrates: Multi-metric comparative screening (Starting Price, Ending Price, Return, Trading Days)
-- Business Purpose: Identify the most successful wealth-creating stocks in the Indian market over 25+ years.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    sumry.first_trading_date,
    sumry.starting_price,
    sumry.ending_price,
    ROUND(sumry.ending_price / NULLIF(sumry.starting_price, 0), 2) AS price_multiplication_factor,
    sumry.total_return_pct,
    sumry.total_trading_days
FROM stock_summary sumry
INNER JOIN company c ON sumry.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE sumry.total_return_pct > 0
ORDER BY sumry.total_return_pct DESC
LIMIT 10;

-- Query 7.2: Risk-Adjusted Return Efficiency Ranking (Return-to-Volatility Ratio)
-- Demonstrates: Ratio of return to volatility proxying a historical Sharpe-like ranking
-- Business Purpose: Discover equities that generated the highest return per unit of realized volatility.
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    sumry.total_return_pct,
    sumry.volatility_pct,
    ROUND(sumry.total_return_pct / NULLIF(sumry.volatility_pct, 0), 2) AS return_to_volatility_ratio,
    sumry.avg_daily_return_pct
FROM stock_summary sumry
INNER JOIN company c ON sumry.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE sumry.total_return_pct > 0 
  AND sumry.volatility_pct > 0
ORDER BY return_to_volatility_ratio DESC
LIMIT 15;

-- Query 7.3: Outperformance vs Equal-Weighted Market Benchmark
-- Demonstrates: CTE computing global average daily return across all stocks, comparing each stock's alpha
-- Business Purpose: Benchmark each company against the equal-weighted Nifty 50 average.
WITH MarketBenchmark AS (
    SELECT 
        ROUND(AVG(avg_daily_return_pct), 4) AS market_avg_daily_return,
        ROUND(AVG(volatility_pct), 4) AS market_avg_volatility
    FROM stock_summary
)
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    sumry.avg_daily_return_pct AS stock_daily_return,
    b.market_avg_daily_return,
    ROUND(sumry.avg_daily_return_pct - b.market_avg_daily_return, 4) AS daily_alpha_pct,
    sumry.volatility_pct,
    b.market_avg_volatility
FROM stock_summary sumry
CROSS JOIN MarketBenchmark b
INNER JOIN company c ON sumry.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
ORDER BY daily_alpha_pct DESC
LIMIT 15;

-- Query 7.4: Recent 1-Year Performance Leaderboard (2025 to 2026)
-- Demonstrates: CTE computing start-of-year close vs end-of-year close directly from daily price history
-- Business Purpose: Measure trailing 1-year momentum and spot recent outperformers vs laggards.
WITH YearPriceEndpoints AS (
    SELECT 
        ticker,
        (ARRAY_AGG(close_price ORDER BY trading_date ASC))[1] AS price_start_2025,
        (ARRAY_AGG(close_price ORDER BY trading_date DESC))[1] AS price_end_2026
    FROM daily_price_history
    WHERE trading_date BETWEEN '2025-01-01' AND '2026-01-30'
    GROUP BY ticker
)
SELECT 
    c.ticker,
    c.company_name,
    s.sector_name,
    ROUND(ep.price_start_2025, 2) AS price_jan_2025,
    ROUND(ep.price_end_2026, 2) AS price_jan_2026,
    ROUND(((ep.price_end_2026 - ep.price_start_2025) / ep.price_start_2025) * 100, 2) AS trailing_1yr_return_pct
FROM YearPriceEndpoints ep
INNER JOIN company c ON ep.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
ORDER BY trailing_1yr_return_pct DESC
LIMIT 15;

-- Query 7.5: Market Performance on Extreme High-Volatility Days
-- Demonstrates: CASE WHEN, aggregate conditional counts and returns on turbulent market days
-- Business Purpose: Assess how different sectors withstand high market volatility sessions (days with Volatility_20D > 3%).
SELECT 
    s.sector_name,
    COUNT(p.trading_date) AS high_vol_trading_sessions,
    ROUND(AVG(p.daily_return) * 100, 3) AS avg_return_on_high_vol_days,
    ROUND(MIN(p.daily_return) * 100, 2) AS max_single_day_drop_pct,
    ROUND(MAX(p.daily_return) * 100, 2) AS max_single_day_gain_pct
FROM daily_price_history p
INNER JOIN company c ON p.ticker = c.ticker
INNER JOIN sector s ON c.sector_id = s.sector_id
WHERE p.vol_20d >= 0.03
GROUP BY s.sector_name
ORDER BY avg_return_on_high_vol_days DESC;
