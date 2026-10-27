#!/usr/bin/env python3
import os
import subprocess
import psycopg2
import pytest
from fastapi.testclient import TestClient

BACKUP_FILE = "data/backups/stock_timescale_db_pre_migration_20261026.dump"
TEST_DB = "stock_timescale_workflow_test"
TS_PORT = 5434

def run_psql_file(sql_file, db=TEST_DB):
    cmd = f"cat {sql_file} | docker exec -i dbs_timescaledb psql -U postgres -d {db}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Error running {sql_file}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout

def main():
    print(f"=== STEP 1: RESTORING FRESH ISOLATED DATABASE {TEST_DB} FROM HOST BACKUP ===")
    subprocess.run(f"docker exec dbs_timescaledb psql -U postgres -c 'DROP DATABASE IF EXISTS {TEST_DB};'", shell=True, check=True)
    subprocess.run(f"docker exec dbs_timescaledb psql -U postgres -c 'CREATE DATABASE {TEST_DB};'", shell=True, check=True)
    restore_cmd = f"cat {BACKUP_FILE} | docker exec -i dbs_timescaledb pg_restore -U postgres -d {TEST_DB}"
    res = subprocess.run(restore_cmd, shell=True, capture_output=True, text=True)
    assert res.returncode == 0, f"Restore failed: {res.stderr}"
    print("Database restored successfully.")

    conn = psycopg2.connect(f"postgresql://postgres:postgres@localhost:{TS_PORT}/{TEST_DB}")
    conn.autocommit = True
    cur = conn.cursor()

    # Verify initial state
    cur.execute("""
    SELECT h.hypertable_name, h.num_chunks, d.time_interval, (SELECT COUNT(*) FROM public.daily_price_history)
    FROM timescaledb_information.hypertables h
    JOIN timescaledb_information.dimensions d ON h.hypertable_name = d.hypertable_name
    WHERE h.hypertable_name = 'daily_price_history';
    """)
    row = cur.fetchone()
    print(f"Initial State: table={row[0]}, chunks={row[1]}, interval={row[2]}, rows={row[3]}")
    assert row[1] == 1414, "Expected 1414 initial chunks"

    print("\n=== STEP 2: RUNNING STAGING SCRIPT (01_stage_replacement_360d.sql) ===")
    run_psql_file("sql/migration/01_stage_replacement_360d.sql")
    cur.execute("SELECT COUNT(*), (SELECT num_chunks FROM timescaledb_information.hypertables WHERE hypertable_name = 'daily_price_history_360d') FROM public.daily_price_history_360d;")
    staged = cur.fetchone()
    print(f"Staged replacement: rows={staged[0]}, chunks={staged[1]}")
    assert staged[0] == 287310
    assert staged[1] == 28

    print("\n=== STEP 3: RUNNING ATOMIC CUTOVER SCRIPT (02_atomic_cutover.sql) ===")
    run_psql_file("sql/migration/02_atomic_cutover.sql")
    print("Cutover executed.")

    print("\n=== STEP 4: VERIFYING TRIGGER OWNERSHIP AFTER CUTOVER ===")
    cur.execute("""
    SELECT tgname, c.relname, tgrelid::regclass
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    WHERE tgname = 'trg_track_price_history_changes';
    """)
    trg = cur.fetchall()
    print("Trigger attachments found:")
    for t in trg:
        print(f"  Trigger '{t[0]}' attached to table '{t[1]}' (relclass={t[2]})")
    parent_trgs = [t for t in trg if t[1] == "daily_price_history"]
    chunk_trgs = [t for t in trg if t[1].startswith("_hyper_")]
    print(f"Parent table trigger count: {len(parent_trgs)}")
    print(f"Chunk tables inherited trigger count: {len(chunk_trgs)}")
    assert len(parent_trgs) == 1, "Expected exactly 1 trigger attachment on public.daily_price_history"
    assert len(chunk_trgs) == 28, f"Expected 28 chunk trigger inheritances, found {len(chunk_trgs)}"
    print("Confirmed: The trigger is owned by the active hypertable 'daily_price_history' and inherited by all 28 chunks.")

    # Verify backup table has no trigger
    cur.execute("""
    SELECT tgname FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    WHERE c.relname = 'daily_price_history_7d_backup';
    """)
    backup_trgs = cur.fetchall()
    print(f"Backup table triggers count: {len(backup_trgs)}")
    assert len(backup_trgs) == 0, "Backup table unexpectedly has triggers"

    print("\n=== STEP 5: SIMULATING POST-CUTOVER DML & LOGGING VERIFICATION ===")
    # 1. Insert new row
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'TCS.NS', '2026-02-02', 4000.0, 4050.0, 3990.0, 4025.0, 1500000, 0.0125, 0.0150, 3950.0, 3800.0
    );
    """)
    # 2. Update existing row
    cur.execute("UPDATE public.daily_price_history SET close_price = 9999.9999 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    # 3. Delete row
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    # 4. Concurrent modification
    cur.execute("UPDATE public.daily_price_history SET close_price = 7777.7777 WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
    
    # 5. Deliberately unlogged missing historical row (simulate accidental loss in active table)
    cur.execute("ALTER TABLE public.daily_price_history DISABLE TRIGGER trg_track_price_history_changes;")
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
    cur.execute("ALTER TABLE public.daily_price_history ENABLE TRIGGER trg_track_price_history_changes;")
    print("Post-cutover DML executed (Insert, Update, Delete, Concurrent Update, Unlogged Missing).")

    # Verify change log entries
    cur.execute("SELECT operation, ticker, trading_date FROM public.daily_price_history_change_log ORDER BY change_id;")
    logs = cur.fetchall()
    print("Change Log Entries:")
    for l in logs:
        print(f"  operation={l[0]}, ticker={l[1]}, trading_date={l[2]}")
    assert len(logs) == 4, f"Expected 4 logged events, found {len(logs)}"
    ops = [l[0] for l in logs]
    assert "INSERT" in ops and "UPDATE" in ops and "DELETE" in ops

    print("\n=== STEP 6: RUNNING SAFE ROLLBACK SCRIPT (03_safe_rollback.sql) ===")
    run_psql_file("sql/migration/03_safe_rollback.sql")
    print("Rollback script completed.")

    print("\n=== STEP 7: VERIFYING POST-ROLLBACK STATE & DATA PRESERVATION ===")
    cur.execute("""
    SELECT h.hypertable_name, h.num_chunks, d.time_interval
    FROM timescaledb_information.hypertables h
    JOIN timescaledb_information.dimensions d ON h.hypertable_name = d.hypertable_name
    WHERE h.hypertable_name = 'daily_price_history';
    """)
    rb_state = cur.fetchone()
    print(f"Restored hypertable: name={rb_state[0]}, chunks={rb_state[1]}, interval={rb_state[2]}")
    assert rb_state[1] == 1414, "Expected 1414 chunks after rollback"
    assert "7 days" in str(rb_state[2]), "Expected 7-day interval after rollback"

    # Verify row assertions
    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    assert cur.fetchone()[0] == 1, "Post-cutover INSERT was lost!"

    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    assert float(cur.fetchone()[0]) == 9999.9999, "Post-cutover UPDATE was lost!"

    cur.execute("SELECT close_price FROM public.daily_price_history WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
    assert float(cur.fetchone()[0]) == 7777.7777, "Concurrent UPDATE was lost!"

    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'INFY.NS' AND trading_date = '2026-01-30';")
    assert cur.fetchone()[0] == 0, "Logged DELETE was not reconciled!"

    cur.execute("SELECT COUNT(*) FROM public.daily_price_history WHERE ticker = 'WIPRO.NS' AND trading_date = '2026-01-30';")
    assert cur.fetchone()[0] == 1, "Unlogged historical row was erroneously deleted from backup!"
    print("All row reconciliation assertions passed with 100% precision.")

    print("\n=== STEP 8: TESTING COMPATIBILITY VIEW & RUNNING FULL API REGRESSION SUITE ===")
    # Clean up test modifications to match baseline test suite expectations
    cur.execute("DELETE FROM public.daily_price_history WHERE ticker = 'TCS.NS' AND trading_date = '2026-02-02';")
    cur.execute("UPDATE public.daily_price_history SET close_price = 3800.0 WHERE ticker = 'TCS.NS' AND trading_date = '2026-01-30';")
    cur.execute("UPDATE public.daily_price_history SET close_price = 2800.0 WHERE ticker = 'RELIANCE.NS' AND trading_date = '2026-01-30';")
    cur.execute("""
    INSERT INTO public.daily_price_history (
        ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200
    ) VALUES (
        'INFY.NS', '2026-01-30', 1600.0, 1620.0, 1590.0, 1610.0, 1000000, 0.005, 0.012, 1580.0, 1520.0
    ) ON CONFLICT DO NOTHING;
    """)

    cur.execute("SELECT COUNT(*) FROM public.stock_price_history;")
    v_cnt = cur.fetchone()[0]
    print(f"stock_price_history view row count: {v_cnt}")
    assert v_cnt == 287310

    # Run pytest pointing to TEST_DB
    pytest_res = subprocess.run(
        f"TIMESCALE_DB={TEST_DB} venv/bin/pytest tests/test_api.py -v",
        shell=True, capture_output=True, text=True
    )
    print("\nPYTEST OUTPUT:\n" + pytest_res.stdout)
    assert pytest_res.returncode == 0, f"API regression tests failed!\n{pytest_res.stdout}\n{pytest_res.stderr}"

    print("=== WORKFLOW TEST COMPLETED SUCCESSFULLY! ALL GATES PASSED! ===")

if __name__ == "__main__":
    main()
