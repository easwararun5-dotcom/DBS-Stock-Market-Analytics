\set ON_ERROR_STOP on
-- ============================================================================
-- Step 3: Safe Delta-Reconciled Rollback Script
-- Target Database: stock_timescale_db (TimescaleDB on port 5434)
-- ============================================================================

SET lock_timeout = '5s';
SET statement_timeout = '60s';

BEGIN;

-- 1. Pause concurrent writes/reads
LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;
LOCK TABLE public.daily_price_history_7d_backup IN ACCESS EXCLUSIVE MODE;

-- 2. Drop trigger on active table to avoid recursive tracking during rollback
DROP TRIGGER IF EXISTS trg_track_price_history_changes ON public.daily_price_history;

-- 3. Reconcile post-cutover INSERTs and UPDATEs based on the LATEST operation per key
WITH latest_ops AS (
    SELECT DISTINCT ON (ticker, trading_date)
        change_id,
        operation,
        ticker,
        trading_date
    FROM public.daily_price_history_change_log
    ORDER BY ticker, trading_date, change_id DESC
)
INSERT INTO public.daily_price_history_7d_backup (
    ticker, trading_date, open_price, high_price, low_price, close_price,
    volume, daily_return, vol_20d, ma_50, ma_200
)
SELECT 
    v.ticker, v.trading_date, v.open_price, v.high_price, v.low_price, v.close_price,
    v.volume, v.daily_return, v.vol_20d, v.ma_50, v.ma_200
FROM public.daily_price_history v
JOIN latest_ops op ON v.ticker = op.ticker AND v.trading_date = op.trading_date
WHERE op.operation IN ('INSERT', 'UPDATE')
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

-- 4. Reconcile ONLY keys whose LATEST operation was 'DELETE'
WITH latest_ops AS (
    SELECT DISTINCT ON (ticker, trading_date)
        change_id,
        operation,
        ticker,
        trading_date
    FROM public.daily_price_history_change_log
    ORDER BY ticker, trading_date, change_id DESC
)
DELETE FROM public.daily_price_history_7d_backup b
USING latest_ops op
WHERE b.ticker = op.ticker 
  AND b.trading_date = op.trading_date 
  AND op.operation = 'DELETE';

-- 5. Atomic Table Swap Back to 7-Day Hypertable
ALTER TABLE public.daily_price_history RENAME TO daily_price_history_aborted_360d;
ALTER TABLE public.daily_price_history_7d_backup RENAME TO daily_price_history;

-- 6. Explicitly Rebuild Compatibility View (Binds back to 7-day hypertable OID)
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

-- Note: daily_price_history_change_log is preserved intact for post-mortem audit.
COMMIT;
