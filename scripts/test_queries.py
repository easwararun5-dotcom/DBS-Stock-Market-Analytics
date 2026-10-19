#!/usr/bin/env python3
"""
Test Runner for Analytical SQL Query Suite.
Executes all SQL files in sql/queries/ against stock_market_db and validates exit codes.
"""

import os
import sys
import glob
import subprocess
from datetime import datetime

HOST = os.getenv("PGHOST", "localhost")
PORT = os.getenv("PGPORT", "5435")
DBNAME = os.getenv("PGDATABASE", "stock_market_db")
USER = os.getenv("PGUSER", "easwarap")

QUERY_DIR = "sql/queries"

def main():
    files = sorted(glob.glob(os.path.join(QUERY_DIR, "*.sql")))
    if not files:
        print(f"Error: No SQL files found in {QUERY_DIR}")
        sys.exit(1)

    print(f"Running Analytical SQL Test Suite on {DBNAME} (localhost:{PORT})...")
    print("=" * 70)
    print(f"{'Query File':<35} | {'Status':<10} | {'Duration (s)':<12}")
    print("-" * 70)

    total_start = datetime.now()
    failures = 0

    for fpath in files:
        fname = os.path.basename(fpath)
        start = datetime.now()
        
        cmd = [
            "psql",
            "-h", HOST,
            "-p", PORT,
            "-U", USER,
            "-d", DBNAME,
            "-v", "ON_ERROR_STOP=1",
            "-q",
            "-f", fpath
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        dur = (datetime.now() - start).total_seconds()

        if res.returncode == 0:
            print(f"{fname:<35} | {'PASSED':<10} | {dur:<12.3f}")
        else:
            print(f"{fname:<35} | {'FAILED':<10} | {dur:<12.3f}")
            print(f"  STDERR: {res.stderr.strip()}")
            failures += 1

    total_dur = (datetime.now() - total_start).total_seconds()
    print("=" * 70)
    print(f"Total: {len(files)} files executed in {total_dur:.2f}s | Failures: {failures}")

    if failures > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
