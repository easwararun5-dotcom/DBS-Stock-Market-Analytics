\set ON_ERROR_STOP on
-- ============================================================================
-- Step 1: Offline Staging of Fixed 360-Day Replacement Hypertable
-- Target Database: stock_timescale_db (TimescaleDB on port 5434)
-- Note: Zero locking on active production table daily_price_history.
-- ============================================================================

-- 1. Create table structure with identical schema and constraints
DROP TABLE IF EXISTS public.daily_price_history_360d CASCADE;

CREATE TABLE public.daily_price_history_360d (
    ticker text NOT NULL,
    trading_date date NOT NULL,
    open_price numeric(14,4),
    high_price numeric(14,4),
    low_price numeric(14,4),
    close_price numeric(14,4),
    volume bigint,
    daily_return numeric(10,4),
    vol_20d numeric(10,4),
    ma_50 numeric(14,4),
    ma_200 numeric(14,4),
    CONSTRAINT daily_price_history_360d_pkey PRIMARY KEY (ticker, trading_date),
    CONSTRAINT daily_price_history_360d_volume_check CHECK (volume >= 0)
);

-- 2. Convert to TimescaleDB hypertable with fixed 360-day interval
SELECT create_hypertable(
    'public.daily_price_history_360d',
    'trading_date',
    chunk_time_interval => INTERVAL '1 year' -- Stored as fixed 360-day interval (31,104,000,000,000 us)
);

-- 3. Create required secondary indexes
CREATE INDEX idx_dph360d_ticker_date ON public.daily_price_history_360d(ticker, trading_date DESC);
CREATE INDEX idx_dph360d_trading_date ON public.daily_price_history_360d(trading_date DESC);

-- 4. Copy existing dataset from production table
INSERT INTO public.daily_price_history_360d 
SELECT * FROM public.daily_price_history;

-- 5. Update catalog statistics
ANALYZE public.daily_price_history_360d;
