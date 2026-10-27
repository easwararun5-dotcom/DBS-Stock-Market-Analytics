\set ON_ERROR_STOP on
-- ============================================================================
-- Step 2: Atomic Cutover with Lock Timeout, Validation Gates, and Change Tracking
-- Target Database: stock_timescale_db (TimescaleDB on port 5434)
-- ============================================================================

-- Guard against connection pool starvation
SET lock_timeout = '5s';
SET statement_timeout = '60s';

BEGIN;

-- 1. Acquire Exclusive Locks FIRST to freeze both tables and prevent concurrent writes
LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;
LOCK TABLE public.daily_price_history_360d IN ACCESS EXCLUSIVE MODE;

-- 2. Atomic Catch-Up Synchronization (Copies any delta that occurred during the staging window)
INSERT INTO public.daily_price_history_360d (
    ticker, trading_date, open_price, high_price, low_price, close_price,
    volume, daily_return, vol_20d, ma_50, ma_200
)
SELECT 
    s.ticker, s.trading_date, s.open_price, s.high_price, s.low_price, s.close_price,
    s.volume, s.daily_return, s.vol_20d, s.ma_50, s.ma_200
FROM public.daily_price_history s
ON CONFLICT (ticker, trading_date) DO UPDATE SET
    open_price = EXCLUDED.open_price,
    high_price = EXCLUDED.high_price,
    low_price = EXCLUDED.low_price,
    close_price = EXCLUDED.close_price,
    volume = EXCLUDED.volume,
    daily_return = EXCLUDED.daily_return,
    vol_20d = EXCLUDED.vol_20d,
    ma_50 = EXCLUDED.ma_50,
    ma_200 = EXCLUDED.ma_200;

DELETE FROM public.daily_price_history_360d d
WHERE NOT EXISTS (
    SELECT 1 FROM public.daily_price_history s 
    WHERE s.ticker = d.ticker AND s.trading_date = d.trading_date
);

-- 3. Pre-cutover Validation Gates (Guaranteed atomic, synchronized, and race-free under lock)
DO $$
DECLARE
    src_cnt BIGINT;
    dst_cnt BIGINT;
    dst_chunks INT;
    diff_forward_cnt BIGINT;
    diff_backward_cnt BIGINT;
BEGIN
    SELECT COUNT(*) INTO src_cnt FROM public.daily_price_history;
    SELECT COUNT(*) INTO dst_cnt FROM public.daily_price_history_360d;
    
    IF src_cnt != dst_cnt THEN
        RAISE EXCEPTION 'Pre-cutover Gate 1 Failed: Row count mismatch (src=%, dst=%)', src_cnt, dst_cnt;
    END IF;

    SELECT num_chunks INTO dst_chunks 
    FROM timescaledb_information.hypertables 
    WHERE hypertable_name = 'daily_price_history_360d';
    
    IF dst_chunks != 28 THEN
        RAISE EXCEPTION 'Pre-cutover Gate 2 Failed: Expected 28 chunks in replacement, found %', dst_chunks;
    END IF;

    SELECT COUNT(*) INTO diff_forward_cnt FROM (
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
        FROM public.daily_price_history
        EXCEPT
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
        FROM public.daily_price_history_360d
    ) sub;

    SELECT COUNT(*) INTO diff_backward_cnt FROM (
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
        FROM public.daily_price_history_360d
        EXCEPT
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
        FROM public.daily_price_history
    ) sub;

    IF diff_forward_cnt != 0 OR diff_backward_cnt != 0 THEN
        RAISE EXCEPTION 'Pre-cutover Gate 3 Failed: Bidirectional difference detected (missing=%, extra=%)', diff_forward_cnt, diff_backward_cnt;
    END IF;
END $$;

-- 3. Create Change-Tracking Infrastructure
CREATE TABLE IF NOT EXISTS public.daily_price_history_change_log (
    change_id BIGSERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
    changed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    ticker TEXT NOT NULL,
    trading_date DATE NOT NULL,
    old_data JSONB,
    new_data JSONB
);

CREATE OR REPLACE FUNCTION public.fn_track_price_history_changes()
RETURNS TRIGGER AS $func$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.daily_price_history_change_log (operation, ticker, trading_date, new_data)
        VALUES ('INSERT', NEW.ticker, NEW.trading_date, to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO public.daily_price_history_change_log (operation, ticker, trading_date, old_data, new_data)
        VALUES ('UPDATE', NEW.ticker, NEW.trading_date, to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO public.daily_price_history_change_log (operation, ticker, trading_date, old_data)
        VALUES ('DELETE', OLD.ticker, OLD.trading_date, to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$func$ LANGUAGE plpgsql;

-- 4. Atomic Rename Swap
ALTER TABLE public.daily_price_history RENAME TO daily_price_history_7d_backup;
ALTER TABLE public.daily_price_history_360d RENAME TO daily_price_history;

-- 5. Attach Change-Tracking Trigger to the Newly Active Hypertable
CREATE TRIGGER trg_track_price_history_changes
AFTER INSERT OR UPDATE OR DELETE ON public.daily_price_history
FOR EACH ROW EXECUTE FUNCTION public.fn_track_price_history_changes();

-- 6. Explicitly Rebuild Compatibility View (Binds to new hypertable OID)
CREATE OR REPLACE VIEW public.stock_price_history AS
SELECT ticker,
   trading_date,
   trading_date::timestamp with time zone AS price_date,
   open_price,
   high_price,
   low_price,
   close_price,
   volume,
   daily_return,
   vol_20d,
   ma_50,
   ma_200
FROM daily_price_history;

-- 7. Ensure Permissions
GRANT ALL ON TABLE public.daily_price_history TO postgres;
GRANT ALL ON TABLE public.stock_price_history TO postgres;
GRANT ALL ON TABLE public.daily_price_history_change_log TO postgres;

COMMIT;
