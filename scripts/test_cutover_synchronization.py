#!/usr/bin/env python3
import subprocess
import psycopg2

BACKUP_FILE = "data/backups/stock_timescale_db_pre_migration_20261026.dump"
TEST_DB = "stock_timescale_staleness_test"
TS_PORT = 5434

def run_psql_file(sql_file, db=TEST_DB):
    cmd = f"cat {sql_file} | docker exec -i dbs_timescaledb psql -v ON_ERROR_STOP=1 -U postgres -d {db}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0 or "ERROR:" in res.stderr:
        raise RuntimeError(f"Error running {sql_file}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout

def main():
    print(f"=== 1. RESTORING ISOLATED DATABASE {TEST_DB} FROM DURABLE BACKUP ===")
    subprocess.run(f"docker exec dbs_timescaledb psql -U postgres -c 'DROP DATABASE IF EXISTS {TEST_DB};'", shell=True, check=True)
    subprocess.run(f"docker exec dbs_timescaledb psql -U postgres -c 'CREATE DATABASE {TEST_DB};'", shell=True, check=True)
    restore_cmd = f"cat {BACKUP_FILE} | docker exec -i dbs_timescaledb pg_restore -U postgres -d {TEST_DB}"
    res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
    assert res.returncode == 0, f"Restore failed: {res.stderr}"

    conn = psycopg2.connect(f"postgresql://postgres:postgres@localhost:{TS_PORT}/{TEST_DB}")
    conn.autocommit = True
    cur = conn.cursor()

    print("\n=== 2. RUNNING STAGING SCRIPT (01_stage_replacement_360d.sql) ===")
    run_psql_file("sql/migration/01_stage_replacement_360d.sql")

    print("\n=== 3. SIMULATING STALENESS: WRITES TO SOURCE TABLE DURING STAGING WINDOW ===")
    # 1. New row inserted into source table
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'TCS.NS', '2026-02-02', 4000.0, 4050.0, 3990.0, 4025.0, 1500000, 0.0125, 0.0150, 3950.0, 3800.0
    );
    """)
    # 2. Existing row updated in source table
    cur.execute("UPDATE public.daily_price_history SET close_price = 8888.8888 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    # 3. Existing row deleted in source table
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    print("Simulated 3 concurrent writes to daily_price_history (Insert, Update, Delete).")
    print("daily_price_history_360d is now STALE relative to daily_price_history.")

    print("\n=== 4. CONFIRMING THAT VALIDATION GATES ABORT CUTOVER WHEN STALE (WITHOUT SYNC) ===")
    try:
        # Attempt cutover without catch-up sync
        run_psql_file("sql/migration/02_atomic_cutover.sql")
        print("ERROR: Cutover should have failed due to validation gates!")
        abort_detected = False
    except RuntimeError as e:
        print("Expected Abort Detected:")
        print("  " + str(e).splitlines()[-1])
        abort_detected = True

    assert abort_detected, "Validation gate failed to detect data divergence!"
    print("Confirmed: Validation gates successfully aborted cutover when data divergence occurred.")

    # Confirm tables are completely unchanged after abort
    cur.execute("SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name = 'daily_price_history';")
    assert cur.fetchone()[0] == "daily_price_history"
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'daily_price_history_7d_backup';")
    assert cur.fetchone()[0] == 0, "Backup table was created despite abort!"
    print("Confirmed: Abort was fully atomic; zero changes applied to database schema or tables.")

    print("\n=== 5. TESTING ATOMIC CATCH-UP SYNCHRONIZATION UNDER EXCLUSIVE LOCK ===")
    # Execute atomic cutover WITH catch-up synchronization under exclusive lock
    cur.execute("""
    SET lock_timeout = '5s';
    SET statement_timeout = '30s';

    BEGIN;

    -- Step A: Acquire exclusive locks first
    LOCK TABLE public.daily_price_history IN ACCESS EXCLUSIVE MODE;
    LOCK TABLE public.daily_price_history_360d IN ACCESS EXCLUSIVE MODE;

    -- Step B: Atomic Catch-Up Synchronization (Copies any delta that occurred during staging window)
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

    -- Step C: Validation Gates under lock
    DO $val$
    DECLARE
        src_cnt BIGINT;
        dst_cnt BIGINT;
        dst_chunks INT;
        diff_fwd BIGINT;
        diff_bwd BIGINT;
    BEGIN
        SELECT COUNT(*) INTO src_cnt FROM public.daily_price_history;
        SELECT COUNT(*) INTO dst_cnt FROM public.daily_price_history_360d;
        
        IF src_cnt != dst_cnt THEN
            RAISE EXCEPTION 'Gate 1 Failed: Row count mismatch (src=%, dst=%)', src_cnt, dst_cnt;
        END IF;

        SELECT num_chunks INTO dst_chunks 
        FROM timescaledb_information.hypertables 
        WHERE hypertable_name = 'daily_price_history_360d';
        
        IF dst_chunks != 28 THEN
            RAISE EXCEPTION 'Gate 2 Failed: Expected 28 chunks, found %', dst_chunks;
        END IF;

        SELECT COUNT(*) INTO diff_fwd FROM (
            SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
            FROM public.daily_price_history
            EXCEPT
            SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
            FROM public.daily_price_history_360d
        ) sub;

        SELECT COUNT(*) INTO diff_bwd FROM (
            SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
            FROM public.daily_price_history_360d
            EXCEPT
            SELECT ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
            FROM public.daily_price_history
        ) sub;

        IF diff_fwd != 0 OR diff_bwd != 0 THEN
            RAISE EXCEPTION 'Gate 3 Failed: Differences found (missing=%, extra=%)', diff_fwd, diff_bwd;
        END IF;
    END $val$;

    -- Step D: Create Change-Tracking Infrastructure
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

    -- Step E: Atomic Table Swap
    ALTER TABLE public.daily_price_history RENAME TO daily_price_history_7d_backup;
    ALTER TABLE public.daily_price_history_360d RENAME TO daily_price_history;

    -- Step F: Attach Change-Tracking Trigger
    CREATE TRIGGER trg_track_price_history_changes
    AFTER INSERT OR UPDATE OR DELETE ON public.daily_price_history
    FOR EACH ROW EXECUTE FUNCTION public.fn_track_price_history_changes();

    -- Step G: Rebuild Compatibility View
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

    -- Step H: Ensure Permissions
    GRANT ALL ON TABLE public.daily_price_history TO postgres;
    GRANT ALL ON TABLE public.stock_price_history TO postgres;
    GRANT ALL ON TABLE public.daily_price_history_change_log TO postgres;

    COMMIT;
    """)
    print("Atomic Cutover WITH catch-up synchronization committed successfully!")

    print("\n=== 6. VERIFYING THAT ALL DELTAS WERE PRESERVED IN ACTIVE 360-DAY HYPERTABLE ===")
    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    assert cur.fetchone()[0] == 1, "Delta INSERT was not synchronized!"
    print("  [✓] Delta INSERT (TCS.NS, 2026-02-02) was successfully synchronized into active table.")

    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    assert float(cur.fetchone()[0]) == 8888.8888, "Delta UPDATE was not synchronized!"
    print("  [✓] Delta UPDATE (TCS.NS, 2026-01-30, 8888.8888) was successfully synchronized into active table.")

    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    assert cur.fetchone()[0] == 0, "Delta DELETE was not synchronized!"
    print("  [✓] Delta DELETE (INFY.NS, 2026-01-30) was successfully synchronized into active table.")

    cur.execute("SELECT num_chunks, time_interval FROM timescaledb_information.hypertables h JOIN timescaledb_information.dimensions d ON h.hypertable_name = d.hypertable_name WHERE h.hypertable_name = 'daily_price_history';")
    ht_meta = cur.fetchone()
    print(f"Active hypertable: chunks={ht_meta[0]}, interval={ht_meta[1]}")
    assert ht_meta[0] == 28
    assert "360 days" in str(ht_meta[1])

    print("\n=== ALL STALENESS SYNCHRONIZATION AND ABORT TESTS PASSED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    main()
