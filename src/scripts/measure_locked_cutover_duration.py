#!/usr/bin/env python3
import psycopg2
import time

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5434/stock_timescale_seq_test")
conn.autocommit = True
cur = conn.cursor()

# Clean up leftover staging/backup objects
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_360d CASCADE;")
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_7d_backup CASCADE;")
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_aborted_360d CASCADE;")

# Staging
cur.execute("""
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
""")
cur.execute("SELECT create_hypertable('public.daily_price_history_360d', 'trading_date', chunk_time_interval => INTERVAL '1 year');")
cur.execute("CREATE INDEX idx_dph360d_ticker_date ON public.daily_price_history_360d(ticker, trading_date DESC);")
cur.execute("CREATE INDEX idx_dph360d_trading_date ON public.daily_price_history_360d(trading_date DESC);")
cur.execute("INSERT INTO public.daily_price_history_360d SELECT * FROM public.daily_price_history;")

conn.autocommit = False

# Measure exact locked duration of 02_atomic_cutover.sql
cur.execute("SET lock_timeout = '5s';")
cur.execute("SET statement_timeout = '60s';")

t_begin = time.perf_counter()
cur.execute("BEGIN;")

t_lock_start = time.perf_counter()
cur.execute("LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;")
cur.execute("LOCK TABLE public.daily_price_history_360d IN ACCESS EXCLUSIVE MODE;")
t_lock_acquired = time.perf_counter()

# Catch-up sync
cur.execute("""
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
""")
cur.execute("""
DELETE FROM public.daily_price_history_360d d
WHERE NOT EXISTS (
    SELECT 1 FROM public.daily_price_history s 
    WHERE s.ticker = d.ticker AND s.trading_date = d.trading_date
);
""")
t_sync_done = time.perf_counter()

# Validation gates
cur.execute("""
DO $gate$
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
        RAISE EXCEPTION 'Gate 1 Failed';
    END IF;
    SELECT num_chunks INTO dst_chunks FROM timescaledb_information.hypertables WHERE hypertable_name = 'daily_price_history_360d';
    IF dst_chunks != 28 THEN
        RAISE EXCEPTION 'Gate 2 Failed';
    END IF;
    SELECT COUNT(*) INTO diff_forward_cnt FROM (
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200 FROM public.daily_price_history
        EXCEPT
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200 FROM public.daily_price_history_360d
    ) sub;
    SELECT COUNT(*) INTO diff_backward_cnt FROM (
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200 FROM public.daily_price_history_360d
        EXCEPT
        SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200 FROM public.daily_price_history
    ) sub;
    IF diff_forward_cnt != 0 OR diff_backward_cnt != 0 THEN
        RAISE EXCEPTION 'Gate 3 Failed';
    END IF;
END $gate$;
""")
t_val_done = time.perf_counter()

# DDL: Infrastructure, renames, trigger, view, grants
cur.execute("""
CREATE TABLE IF NOT EXISTS public.daily_price_history_change_log (
    change_id BIGSERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL,
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

ALTER TABLE public.daily_price_history RENAME TO daily_price_history_7d_backup;
ALTER TABLE public.daily_price_history_360d RENAME TO daily_price_history;

CREATE TRIGGER trg_track_price_history_changes
AFTER INSERT OR UPDATE OR DELETE ON public.daily_price_history
FOR EACH ROW EXECUTE FUNCTION public.fn_track_price_history_changes();

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

GRANT ALL ON TABLE public.daily_price_history TO postgres;
GRANT ALL ON TABLE public.stock_price_history TO postgres;
GRANT ALL ON TABLE public.daily_price_history_change_log TO postgres;
""")
t_ddl_done = time.perf_counter()

# Commit
cur.execute("COMMIT;")
t_commit_done = time.perf_counter()

lock_acquire_time = (t_lock_acquired - t_lock_start) * 1000
sync_time = (t_sync_done - t_lock_acquired) * 1000
val_time = (t_val_done - t_sync_done) * 1000
ddl_time = (t_ddl_done - t_val_done) * 1000
commit_time = (t_commit_done - t_ddl_done) * 1000
total_lock_hold_duration = (t_commit_done - t_lock_acquired) * 1000
total_transaction_duration = (t_commit_done - t_begin) * 1000

print(f"MEASURED LOCKED CUTOVER BREAKDOWN (287,310 rows):")
print(f"  1. Lock Acquisition Time:          {lock_acquire_time:>8.2f} ms")
print(f"  2. Catch-Up Sync (Upsert+Delete):  {sync_time:>8.2f} ms ({sync_time/1000:.2f} s)")
print(f"  3. Validation Gates (EXCEPT diffs):{val_time:>8.2f} ms ({val_time/1000:.2f} s)")
print(f"  4. DDL (Swap, Trigger, View):      {ddl_time:>8.2f} ms")
print(f"  5. Transaction Commit:             {commit_time:>8.2f} ms")
print(f"  -------------------------------------------------------------")
print(f"  TOTAL EXCLUSIVE LOCK HOLD DURATION:{total_lock_hold_duration:>8.2f} ms ({total_lock_hold_duration/1000:.2f} s)")
print(f"  TOTAL TRANSACTION DURATION:        {total_transaction_duration:>8.2f} ms ({total_transaction_duration/1000:.2f} s)")
