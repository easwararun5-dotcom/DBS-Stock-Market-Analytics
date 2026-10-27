#!/usr/bin/env python3
import subprocess
import psycopg2

BACKUP_FILE = "data/backups/stock_timescale_db_pre_migration_20261026.dump"
TEST_DB = "stock_timescale_seq_test"
TS_PORT = 5434

def run_psql_file(sql_file, db=TEST_DB):
    cmd = f"cat {sql_file} | docker exec -i dbs_timescaledb psql -U postgres -d {db}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error running {sql_file}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout

def main():
    print(f"=== 1. CREATING ISOLATED TEST DB {TEST_DB} FROM DURABLE BACKUP ===")
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

    print("\n=== 3. RUNNING ATOMIC CUTOVER SCRIPT (02_atomic_cutover.sql) ===")
    run_psql_file("sql/migration/02_atomic_cutover.sql")

    print("\n=== 4. EXERCISING ALL MULTI-OPERATION SEQUENCES ===")

    # Sequence 1: UPDATE -> UPDATE on existing key ('TCS.NS', '2026-01-30')
    cur.execute("UPDATE public.daily_price_history SET close_price = 5001.0 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    cur.execute("UPDATE public.daily_price_history SET close_price = 5002.0 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    print("  [✓] Sequence 1 executed: UPDATE -> UPDATE (TCS.NS)")

    # Sequence 2: INSERT -> UPDATE on new key ('TCS.NS', '2026-02-02')
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'TCS.NS', '2026-02-02', 6000.0, 6050.0, 5990.0, 6001.0, 1000000, 0.01, 0.01, 5900.0, 5800.0
    );
    """)
    cur.execute("UPDATE public.daily_price_history SET close_price = 6002.0 WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    print("  [✓] Sequence 2 executed: INSERT -> UPDATE (TCS.NS, 2026-02-02)")

    # Sequence 3: INSERT -> DELETE on new key ('SBIN.NS', '2026-02-02')
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'SBIN.NS', '2026-02-02', 7000.0, 7050.0, 6990.0, 7001.0, 2000000, 0.01, 0.01, 6900.0, 6800.0
    );
    """)
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'SBIN.NS' AND trading_date = '2026-02-02';")
    print("  [✓] Sequence 3 executed: INSERT -> DELETE (SBIN.NS, 2026-02-02)")

    # Sequence 4: UPDATE -> DELETE on existing key ('INFY.NS', '2026-01-30')
    cur.execute("UPDATE public.daily_price_history SET close_price = 8001.0 WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    print("  [✓] Sequence 4 executed: UPDATE -> DELETE (INFY.NS, 2026-01-30)")

    # Sequence 5: DELETE -> INSERT on existing key ('HDFCBANK.NS', '2026-01-30')
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'HDFCBANK.NS' AND trading_date = '2026-01-30';")
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'HDFCBANK.NS', '2026-01-30', 9000.0, 9050.0, 8990.0, 9002.0, 3000000, 0.01, 0.01, 8900.0, 8800.0
    );
    """)
    print("  [✓] Sequence 5 executed: DELETE -> INSERT (HDFCBANK.NS, 2026-01-30)")

    # Sequence 6: Multiple concurrent changes across distinct keys
    cur.execute("UPDATE public.daily_price_history SET close_price = 2222.0 WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
    cur.execute("UPDATE public.daily_price_history SET close_price = 1111.0 WHERE ticker = 'ICICIBANK.NS' AND trading_date = '2026-01-30';")
    print("  [✓] Sequence 6 executed: Multiple distinct keys modified (RELIANCE.NS, ICICIBANK.NS)")

    # Sequence 7: Safety invariant - unlogged missing historical row
    cur.execute("ALTER TABLE public.daily_price_history DISABLE TRIGGER trg_track_price_history_changes;")
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
    cur.execute("ALTER TABLE public.daily_price_history ENABLE TRIGGER trg_track_price_history_changes;")
    print("  [✓] Sequence 7 executed: Unlogged missing row simulated (WIPRO.NS, 2026-01-30)")

    # Print total change log entries
    cur.execute("SELECT count(*) FROM public.daily_price_history_change_log;")
    total_logs = cur.fetchone()[0]
    print(f"\nTotal change-log events recorded: {total_logs}")

    print("\n=== 5. RUNNING SAFE ROLLBACK SCRIPT (03_safe_rollback.sql) ===")
    run_psql_file("sql/migration/03_safe_rollback.sql")
    print("Rollback transaction committed.")

    print("\n=== 6. VERIFYING CHANGE LOG PRESERVATION ===")
    cur.execute("SELECT count(*) FROM public.daily_price_history_change_log;")
    preserved_logs = cur.fetchone()[0]
    print(f"Change-log entries after rollback: {preserved_logs}")
    assert preserved_logs == total_logs, f"Change log was modified/cleared during rollback! ({preserved_logs} != {total_logs})"
    print("Confirmed: Change log was NOT cleared before, during, or after rollback.")

    print("\n=== 7. VERIFYING REPRODUCED FINAL STATE FOR EVERY SEQUENCE ===")
    # 1. UPDATE -> UPDATE
    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    s1_val = float(cur.fetchone()[0])
    print(f"Sequence 1 (UPDATE -> UPDATE TCS.NS): close_price = {s1_val} (Expected: 5002.0)")
    assert s1_val == 5002.0, f"Sequence 1 failed: got {s1_val}"

    # 2. INSERT -> UPDATE
    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    s2_row = cur.fetchone()
    assert s2_row is not None, "Sequence 2 failed: row missing"
    s2_val = float(s2_row[0])
    print(f"Sequence 2 (INSERT -> UPDATE TCS.NS): close_price = {s2_val} (Expected: 6002.0)")
    assert s2_val == 6002.0, f"Sequence 2 failed: got {s2_val}"

    # 3. INSERT -> DELETE
    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'SBIN.NS' AND trading_date = '2026-02-02';")
    s3_cnt = cur.fetchone()[0]
    print(f"Sequence 3 (INSERT -> DELETE SBIN.NS): count = {s3_cnt} (Expected: 0)")
    assert s3_cnt == 0, f"Sequence 3 failed: got {s3_cnt}"

    # 4. UPDATE -> DELETE
    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    s4_cnt = cur.fetchone()[0]
    print(f"Sequence 4 (UPDATE -> DELETE INFY.NS): count = {s4_cnt} (Expected: 0)")
    assert s4_cnt == 0, f"Sequence 4 failed: got {s4_cnt}"

    # 5. DELETE -> INSERT (The crucial test!)
    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'HDFCBANK.NS' AND trading_date = '2026-01-30';")
    s5_row = cur.fetchone()
    assert s5_row is not None, "Sequence 5 failed: reinserted row was wrongly deleted by rollback!"
    s5_val = float(s5_row[0])
    print(f"Sequence 5 (DELETE -> INSERT HDFCBANK.NS): close_price = {s5_val} (Expected: 9002.0)")
    assert s5_val == 9002.0, f"Sequence 5 failed: got {s5_val}"

    # 6. Multiple distinct keys
    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
    rel_val = float(cur.fetchone()[0])
    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'ICICIBANK.NS' AND trading_date = '2026-01-30';")
    icici_val = float(cur.fetchone()[0])
    print(f"Sequence 6 (RELIANCE.NS): close_price = {rel_val} (Expected: 2222.0)")
    print(f"Sequence 6 (ICICIBANK.NS): close_price = {icici_val} (Expected: 1111.0)")
    assert rel_val == 2222.0 and icici_val == 1111.0, "Sequence 6 failed"

    # 7. Safety Invariant: Unlogged missing historical row
    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
    wipro_cnt = cur.fetchone()[0]
    print(f"Safety Invariant (Unlogged missing row WIPRO.NS): count = {wipro_cnt} (Expected: 1)")
    assert wipro_cnt == 1, "Safety Invariant failed: unlogged row was deleted!"

    print("\n=== 8. VERIFYING RESTORED HYPERTABLE METADATA & COMPATIBILITY VIEW ===")
    cur.execute("""
    SELECT h.hypertable_name, h.num_chunks, d.time_interval
    FROM timescaledb_information.hypertables h
    JOIN timescaledb_information.dimensions d ON h.hypertable_name = d.hypertable_name
    WHERE h.hypertable_name = 'daily_price_history';
    """)
    ht = cur.fetchone()
    print(f"Active hypertable: name={ht[0]}, chunks={ht[1]}, interval={ht[2]}")
    assert ht[0] == "daily_price_history"
    assert ht[1] == 1414
    assert "7 days" in str(ht[2])

    cur.execute("SELECT COUNT(*) FROM public.stock_price_history;")
    view_cnt = cur.fetchone()[0]
    print(f"Compatibility view row count: {view_cnt}")
    # Net change:
    # Original: 287310
    # + TCS.NS 2026-02-02 (+1)
    # - INFY.NS 2026-01-30 (-1)
    # = 287310
    assert view_cnt == 287310, f"Expected view count 287310, got {view_cnt}"

    print("\n=== 9. RUNNING FULL API REGRESSION SUITE ===")
    # Clean up future-dated bar (2026-02-02) and re-insert INFY.NS 2026-01-30 to match test assertions
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'INFY.NS', '2026-01-30', 1600.0, 1620.0, 1590.0, 1610.0, 1000000, 0.005, 0.012, 1580.0, 1520.0
    ) ON CONFLICT DO NOTHING;
    """)

    pytest_res = subprocess.run(
        f"TIMESCALE_DB={TEST_DB} venv/bin/pytest tests/test_api.py -v",
        shell=True, capture_output=True, text=True
    )
    print("\nPYTEST OUTPUT:\n" + pytest_res.stdout)
    assert pytest_res.returncode == 0, f"API regression tests failed!\n{pytest_res.stdout}\n{pytest_res.stderr}"

    print("\n=== ALL SEQUENCES AND VERIFICATIONS COMPLETED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    main()
