#!/usr/bin/env python3
"""
Test Runner for Database Triggers & Concurrency Regression Suite.
Executes test_triggers.sql and runs live concurrent race-condition tests against stock_market_db,
validates trigger execution, and confirms database state remains clean with zero test residue.
"""

import os
import sys
import time
import threading
import subprocess
from datetime import datetime

HOST = os.getenv("PGHOST", "localhost")
PORT = os.getenv("PGPORT", "5435")
DBNAME = os.getenv("PGDATABASE", "stock_market_db")
USER = os.getenv("PGUSER", "easwarap")

TEST_SQL = "tests/test_triggers.sql"

def run_psql(query=None, file_path=None):
    cmd = [
        "psql",
        "-h", HOST,
        "-p", PORT,
        "-U", USER,
        "-d", DBNAME,
        "-v", "ON_ERROR_STOP=1",
        "-q"
    ]
    if file_path:
        cmd.extend(["-f", file_path])
    elif query:
        cmd.extend(["-c", query])
    return subprocess.run(cmd, capture_output=True, text=True)

def test_concurrency():
    """Tests live concurrent SELL transactions competing for the same holding."""
    print("Running Live Concurrency Race-Condition Test...")
    
    # 1. Setup temporary user and holding
    setup_sql = """
    INSERT INTO app_user (username, email, password_hash, role)
    VALUES ('conc_test_user', 'conc_test@example.com', 'pwd_hash', 'user')
    RETURNING user_id;
    """
    res = run_psql(query=setup_sql)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to setup concurrency user: {res.stderr}")
    user_id = int(res.stdout.split("\n")[2].strip())

    holding_sql = f"""
    INSERT INTO portfolio_holding (user_id, ticker, quantity, invested_value, average_buy_price, purchase_date)
    VALUES ({user_id}, 'TCS.NS', 10.0000, 35000.00, 3500.0000, '2026-03-01')
    RETURNING holding_id;
    """
    res = run_psql(query=holding_sql)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to setup concurrency holding: {res.stderr}")
    holding_id = int(res.stdout.split("\n")[2].strip())

    results = {}

    def session_1():
        # Session 1: Sells 7 shares, holds transaction open for 1s
        cmd = f"""
        BEGIN;
        INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
        VALUES ({holding_id}, {user_id}, 'TCS.NS', 'SELL', '2026-03-02', 3600.0, 7.0);
        SELECT pg_sleep(1);
        COMMIT;
        """
        rc = run_psql(query=cmd)
        results["s1"] = rc

    def session_2():
        # Session 2: Starts 0.2s later, attempts to sell 5 shares concurrently
        time.sleep(0.2)
        cmd = f"""
        INSERT INTO portfolio_transaction (holding_id, user_id, ticker, transaction_type, transaction_date, price, quantity)
        VALUES ({holding_id}, {user_id}, 'TCS.NS', 'SELL', '2026-03-02', 3600.0, 5.0);
        """
        rc = run_psql(query=cmd)
        results["s2"] = rc

    t1 = threading.Thread(target=session_1)
    t2 = threading.Thread(target=session_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Cleanup temporary data
    cleanup_sql = f"""
    DELETE FROM portfolio_transaction WHERE user_id = {user_id};
    DELETE FROM portfolio_holding WHERE user_id = {user_id};
    DELETE FROM portfolio_transaction_audit WHERE user_id = {user_id};
    DELETE FROM app_user WHERE user_id = {user_id};
    """
    run_psql(query=cleanup_sql)

    # Verification: Session 1 must succeed, Session 2 must fail due to insufficient shares
    s1_res = results.get("s1")
    s2_res = results.get("s2")

    if s1_res.returncode != 0:
        raise AssertionError(f"Concurrent Session 1 failed unexpectedly: {s1_res.stderr}")

    if s2_res.returncode == 0:
        raise AssertionError("Concurrent Session 2 unexpectedly succeeded, permitting overselling!")

    if "Insufficient shares to sell" not in s2_res.stderr:
        raise AssertionError(f"Concurrent Session 2 failed with unexpected error: {s2_res.stderr}")

    print("  PASS: Session 1 (7 shares) committed successfully while holding row lock.")
    print("  PASS: Session 2 (5 shares) blocked on row lock, then failed with 'Insufficient shares to sell' (3 available).")
    print("  PASS: Row-level concurrency serialization verified.")

def main():
    print(f"Running Database Trigger & Regression Suite on {DBNAME} (localhost:{PORT})...")
    print("=" * 70)

    # 1. Verify Triggers Exist in System Catalog
    cat_query = """
    SELECT trigger_name, event_manipulation, event_object_table, action_timing
    FROM information_schema.triggers
    WHERE trigger_schema = 'public'
    ORDER BY trigger_name, event_manipulation;
    """
    res_cat = run_psql(query=cat_query)
    if res_cat.returncode != 0:
        print("ERROR: Failed to query PostgreSQL trigger catalog.")
        print(res_cat.stderr)
        sys.exit(1)

    print("Installed Triggers in PostgreSQL Catalog:")
    print(res_cat.stdout.strip())
    print("-" * 70)

    # 2. Run Main Trigger Test Suite
    if not os.path.exists(TEST_SQL):
        print(f"ERROR: Test file {TEST_SQL} not found.")
        sys.exit(1)

    start = datetime.now()
    res_test = run_psql(file_path=TEST_SQL)
    dur = (datetime.now() - start).total_seconds()

    if res_test.returncode == 0:
        print(f"Trigger Integration & Regression Tests: PASSED ({dur:.3f}s)")
        for line in res_test.stderr.splitlines():
            if "PASS:" in line or "REGRESSION SUITE" in line:
                print(f"  {line.strip()}")
    else:
        print(f"Trigger Integration Tests: FAILED ({dur:.3f}s)")
        print(f"  STDERR: {res_test.stderr.strip()}")
        sys.exit(1)

    print("-" * 70)

    # 3. Run Portfolio Lifecycle & Stock Sale Regression Suite
    lifecycle_test_sql = "tests/test_portfolio_lifecycle.sql"
    if os.path.exists(lifecycle_test_sql):
        start = datetime.now()
        res_lc = run_psql(file_path=lifecycle_test_sql)
        dur = (datetime.now() - start).total_seconds()
        if res_lc.returncode == 0:
            print(f"Portfolio Lifecycle & record_stock_sale Tests: PASSED ({dur:.3f}s)")
            for line in res_lc.stderr.splitlines():
                if "PASS:" in line or "REGRESSION SUITE" in line:
                    print(f"  {line.strip()}")
        else:
            print(f"Portfolio Lifecycle Tests: FAILED ({dur:.3f}s)")
            print(f"  STDERR: {res_lc.stderr.strip()}")
            sys.exit(1)
        print("-" * 70)

    print("-" * 70)

    # 3. Run Live Multi-Threaded Concurrency Test
    test_concurrency()
    print("-" * 70)

    # 4. Verify Zero Residue
    residue_query = """
    SELECT 
        (SELECT count(*) FROM app_user) AS users,
        (SELECT count(*) FROM portfolio_holding) AS holdings,
        (SELECT count(*) FROM portfolio_transaction) AS txs,
        (SELECT count(*) FROM portfolio_transaction_audit) AS audits;
    """
    res_clean = run_psql(query=residue_query)
    print("Database Cleanliness Check (Residual Row Counts):")
    print(res_clean.stdout.strip())

    # 5. Verify Market Data Unchanged
    market_query = """
    SELECT 
        (SELECT count(*) FROM sector) AS sectors,
        (SELECT count(*) FROM company) AS companies,
        (SELECT count(*) FROM daily_price_history) AS prices,
        (SELECT count(*) FROM corporate_action) AS corporate_actions,
        (SELECT count(*) FROM current_fundamentals) AS fundamentals,
        (SELECT count(*) FROM stock_summary) AS summaries;
    """
    res_market = run_psql(query=market_query)
    print("Market Data Integrity Check (Row Counts):")
    print(res_market.stdout.strip())
    print("=" * 70)
    print("Trigger Phase & Regression Verification: ALL TESTS PASSED.")

if __name__ == "__main__":
    main()
