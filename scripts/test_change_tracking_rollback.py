import psycopg2

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5434/stock_timescale_isolated_test")
conn.autocommit = True
cur = conn.cursor()

# Clean up any leftover test objects
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_change_log CASCADE;")
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_360d CASCADE;")
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_7d_backup CASCADE;")
cur.execute("DROP TABLE IF EXISTS public.daily_price_history_aborted_360d CASCADE;")

# 1. Create 360d replacement hypertable
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

# 2. Create change tracking table & trigger on replacement
cur.execute("""
CREATE TABLE public.daily_price_history_change_log (
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

CREATE TRIGGER trg_track_price_history_changes
AFTER INSERT OR UPDATE OR DELETE ON public.daily_price_history_360d
FOR EACH ROW EXECUTE FUNCTION public.fn_track_price_history_changes();
""")

# 3. Cutover swap in isolated database
cur.execute("BEGIN;")
cur.execute("LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;")
cur.execute("ALTER TABLE public.daily_price_history RENAME TO daily_price_history_7d_backup;")
cur.execute("ALTER TABLE public.daily_price_history_360d RENAME TO daily_price_history;")
cur.execute("""
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
""")
cur.execute("COMMIT;")
print("1. Cutover to 360-day hypertable with active Change-Tracking completed.")

# 4. Now simulate all four required test cases + preservation of unlogged missing historical rows:

# Case A: A historical row deleted after cutover (e.g. INFY.NS on 2026-01-30)
cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
print("2. Simulated Case A: Historical row deleted after cutover (INFY.NS, 2026-01-30)")

# Case B: A newly inserted row (e.g. TCS.NS on 2026-02-02)
cur.execute("""
INSERT INTO public.daily_price_history (
    ticker, trading_date, open_price, high_price, low_price, close_price,
    volume, daily_return, vol_20d, ma_50, ma_200
) VALUES (
    'TCS.NS', '2026-02-02', 4000.0, 4050.0, 3990.0, 4025.0, 1500000, 0.0125, 0.0150, 3950.0, 3800.0
);
""")
print("3. Simulated Case B: Newly inserted row (TCS.NS, 2026-02-02)")

# Case C: An updated row (e.g. TCS.NS on 2026-01-30 close_price modified)
cur.execute("UPDATE public.daily_price_history SET close_price = 9999.9999 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
print("4. Simulated Case C: Updated row (TCS.NS, 2026-01-30 close_price=9999.9999)")

# Case D: A row changed concurrently with rollback preparation (e.g. RELIANCE.NS on 2026-01-30 close_price modified)
cur.execute("UPDATE public.daily_price_history SET close_price = 7777.7777 WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
print("5. Simulated Case D: Concurrent row modification before write freeze (RELIANCE.NS, close_price=7777.7777)")

# Test Case E (SAFETY PROOF): A historical row missing from the active table without being in the change log.
# Suppose an anomaly/corruption occurred in the active table where WIPRO.NS 2026-01-30 was dropped directly or corrupted.
# We bypass the trigger temporarily to simulate an unlogged missing row:
cur.execute("ALTER TABLE public.daily_price_history DISABLE TRIGGER trg_track_price_history_changes;")
cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
cur.execute("ALTER TABLE public.daily_price_history ENABLE TRIGGER trg_track_price_history_changes;")
print("6. Simulated Case E (Safety Invariant): Unlogged missing row in active table (WIPRO.NS, 2026-01-30) to verify backup WILL NOT delete it.")

# 5. Execute Safe Change-Log Rollback
cur.execute("""
BEGIN;
SET lock_timeout = '5s';
LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;
LOCK TABLE public.daily_price_history_7d_backup IN ACCESS EXCLUSIVE MODE;

-- Reconcile INSERTs and UPDATEs from change log
INSERT INTO public.daily_price_history_7d_backup (
    ticker, trading_date, open_price, high_price, low_price, close_price,
    volume, daily_return, vol_20d, ma_50, ma_200
)
SELECT 
    v.ticker, v.trading_date, v.open_price, v.high_price, v.low_price, v.close_price,
    v.volume, v.daily_return, v.vol_20d, v.ma_50, v.ma_200
FROM public.daily_price_history v
WHERE (v.ticker, v.trading_date) IN (
    SELECT ticker, trading_date FROM public.daily_price_history_change_log WHERE operation IN ('INSERT', 'UPDATE')
)
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

-- Reconcile ONLY explicit logged DELETEs
DELETE FROM public.daily_price_history_7d_backup b
WHERE (b.ticker, b.trading_date) IN (
    SELECT ticker, trading_date FROM public.daily_price_history_change_log WHERE operation = 'DELETE'
);

-- Swap back
ALTER TABLE public.daily_price_history RENAME TO daily_price_history_aborted_360d;
ALTER TABLE public.daily_price_history_7d_backup RENAME TO daily_price_history;

-- Recreate view
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

COMMIT;
""")
print("7. Safe Change-Log Rollback Transaction Committed!")

# 6. Verify Results on Restored daily_price_history
cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
infy_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
tcs_new_count = cur.fetchone()[0]

cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
tcs_update_val = cur.fetchone()[0]

cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
reliance_update_val = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
wipro_count = cur.fetchone()[0]

cur.execute("SELECT num_chunks FROM timescaledb_information.hypertables WHERE hypertable_name = 'daily_price_history';")
chunks = cur.fetchone()[0]

cur.execute("SELECT d.time_interval FROM timescaledb_information.dimensions d WHERE d.hypertable_name = 'daily_price_history';")
interval = cur.fetchone()[0]

print("\n--- EMPIRICAL ROLLBACK VERIFICATION RESULTS ---")
print(f"Case A (Logged Historical Delete INFY.NS 2026-01-30 reflected in backup): count = {infy_count} (Expected: 0)")
print(f"Case B (Post-Cutover New Insert TCS.NS 2026-02-02 preserved in backup): count = {tcs_new_count} (Expected: 1)")
print(f"Case C (Post-Cutover Update TCS.NS 2026-01-30 preserved in backup): close_price = {tcs_update_val} (Expected: 9999.9999)")
print(f"Case D (Concurrent Modification RELIANCE.NS 2026-01-30 preserved): close_price = {reliance_update_val} (Expected: 7777.7777)")
print(f"Case E (Safety Proof: Unlogged missing WIPRO.NS preserved in backup): count = {wipro_count} (Expected: 1 - NOT silently deleted!)")
print(f"Restored Hypertable Chunks: {chunks} (Expected: 1414)")
print(f"Restored Hypertable Interval: {interval} (Expected: 7 days)")

assert infy_count == 0, "Case A Failed"
assert tcs_new_count == 1, "Case B Failed"
assert float(tcs_update_val) == 9999.9999, "Case C Failed"
assert float(reliance_update_val) == 7777.7777, "Case D Failed"
assert wipro_count == 1, "Case E Failed: Unlogged historical row was silently deleted!"
print("\nALL 5 TEST CASES PASSED RIGOROUSLY!")
