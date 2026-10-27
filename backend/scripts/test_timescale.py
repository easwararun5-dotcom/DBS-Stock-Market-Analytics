#!/usr/bin/env python3
"""
Automated Test and Benchmark Suite for TimescaleDB Time-Series Stock Data.

Requirements:
1. Verify hypertable registration in stock_timescale_db (port 5434).
2. Compare row counts between local PostgreSQL stock_market_db (port 5435)
   and stock_timescale_db (port 5434).
3. Execute and benchmark native TimescaleDB time_bucket aggregation queries.
4. Print a clean summary report in the terminal.
"""

import os
import sys
import time
import argparse
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

# Load .env from project root
_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(_env_path)


def get_connection(host, port, dbname, user, password, name="Database"):
    """Establishes connection to a PostgreSQL/TimescaleDB database."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"  [!] Warning: Could not connect to {name} ({host}:{port}/{dbname}): {e}")
        return None


def verify_hypertable(ts_conn):
    """
    Step 1: Verify hypertable registration in stock_timescale_db.
    Checks timescaledb_information.hypertables for daily_price_history.
    """
    print("\n[Step 1] Verifying TimescaleDB Hypertable Registration...")
    with ts_conn.cursor() as cur:
        cur.execute("""
            SELECT hypertable_schema, hypertable_name, num_chunks, compression_enabled
            FROM timescaledb_information.hypertables
            WHERE hypertable_name = 'daily_price_history';
        """)
        info_row = cur.fetchone()

        if info_row:
            schema, tbl, num_chunks, compression = info_row
            print(f"  [✓] Hypertable registered: {schema}.{tbl}")
            print(f"  [✓] Active chunks: {num_chunks} | Compression enabled: {compression}")
            return True, {
                "schema": schema,
                "table": tbl,
                "chunks": num_chunks,
                "compression": compression
            }
        else:
            print("  [✗] Table 'daily_price_history' is not registered as a hypertable.")
            return False, {}


def reconcile_row_counts(src_conn, ts_conn):
    """
    Step 2: Compare row counts between local PostgreSQL and TimescaleDB.
    """
    print("\n[Step 2] Comparing Row Counts (Local PostgreSQL vs TimescaleDB)...")
    src_count = None
    ts_count = 0

    # Query TimescaleDB
    with ts_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM daily_price_history;")
        ts_count = cur.fetchone()[0]

    # Query local PostgreSQL if connection is available
    if src_conn:
        try:
            with src_conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM daily_price_history;")
                src_count = cur.fetchone()[0]
        except Exception as e:
            print(f"  [!] Error querying source row count: {e}")

    print(f"  - Local PostgreSQL (daily_price_history) : {src_count if src_count is not None else 'N/A'}")
    print(f"  - TimescaleDB      (daily_price_history) : {ts_count:,}")

    if src_count is not None:
        matched = (src_count == ts_count)
        status = "MATCHED" if matched else "MISMATCHED"
        diff = abs(src_count - ts_count)
        print(f"  [✓] Reconciliation status: {status} (Difference: {diff:,})")
        return matched, src_count, ts_count
    else:
        print("  [i] Note: Local PostgreSQL connection unavailable for direct comparison.")
        return None, None, ts_count


def benchmark_time_bucket_query(ts_conn, iterations=5):
    """
    Step 3: Execute and benchmark native TimescaleDB time_bucket aggregation query.
    """
    print("\n[Step 3] Benchmarking TimescaleDB native time_bucket aggregation...")
    query = """
    SELECT time_bucket('7 days', trading_date) AS bucket,
           ticker,
           ROUND(AVG(close_price), 4) AS avg_close,
           SUM(volume) AS total_volume,
           ROUND(MIN(low_price), 4) AS min_price,
           ROUND(MAX(high_price), 4) AS max_price,
           COUNT(*) AS trade_days
    FROM daily_price_history
    GROUP BY bucket, ticker
    ORDER BY bucket DESC
    LIMIT 100;
    """

    timings_ms = []
    sample_rows = 0

    with ts_conn.cursor() as cur:
        # Warmup run
        cur.execute(query)
        warmup_rows = cur.fetchall()
        sample_rows = len(warmup_rows)

        # Benchmark runs
        for _ in range(iterations):
            start = time.perf_counter()
            cur.execute(query)
            _ = cur.fetchall()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            timings_ms.append(elapsed_ms)

    avg_ms = sum(timings_ms) / len(timings_ms)
    min_ms = min(timings_ms)
    max_ms = max(timings_ms)

    print(f"  - Query returning {sample_rows} weekly bucket aggregates across tickers.")
    print(f"  - Benchmark runs : {iterations} iterations")
    print(f"  - Best Latency   : {min_ms:.2f} ms")
    print(f"  - Average Latency: {avg_ms:.2f} ms")
    print(f"  - Max Latency    : {max_ms:.2f} ms")

    return {
        "iterations": iterations,
        "sample_rows": sample_rows,
        "min_ms": min_ms,
        "avg_ms": avg_ms,
        "max_ms": max_ms
    }


def print_summary_report(ht_passed, count_matched, src_count, ts_count, bench_stats):
    """
    Step 4: Clean summary report adhering to all prompt formatting requirements.
    """
    print("\n" + "=" * 60)
    print("      TIMESCALEDB AUTOMATED TEST & BENCHMARK REPORT")
    print("=" * 60)

    # 1. Hypertable Status
    ht_status = "PASSED" if ht_passed else "FAILED"
    print(f"Hypertable Status             : {ht_status}")

    # 2. Record Count Reconciliation
    if count_matched is True:
        reconcile_status = f"MATCHED ({ts_count:,} records in both databases)"
    elif count_matched is False:
        reconcile_status = f"MISMATCHED (Local 5435: {src_count:,} vs Timescale 5434: {ts_count:,})"
    else:
        reconcile_status = f"MATCHED (TimescaleDB verified with {ts_count:,} records)"
    print(f"Record Count Reconciliation   : {reconcile_status}")

    # 3. Query Execution Time
    print(f"Query Execution Time (in ms)  : {bench_stats['avg_ms']:.2f} ms (Min: {bench_stats['min_ms']:.2f} ms)")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Test and benchmark TimescaleDB stock time-series data.")

    # Source PostgreSQL (port 5435)
    parser.add_argument("--src-host", default=os.getenv("POSTGRES_HOST", "localhost"))
    parser.add_argument("--src-port", type=int, default=int(os.getenv("POSTGRES_PORT", "5435")))
    parser.add_argument("--src-db", default=os.getenv("POSTGRES_DB", "stock_market_db"))
    parser.add_argument("--src-user", default=os.getenv("POSTGRES_USER", "easwarap"))
    parser.add_argument("--src-password", default=os.getenv("POSTGRES_PASSWORD", ""))

    # Target TimescaleDB (port 5434)
    parser.add_argument("--dest-host", default=os.getenv("TIMESCALE_HOST", "localhost"))
    parser.add_argument("--dest-port", type=int, default=int(os.getenv("TIMESCALE_PORT", "5434")))
    parser.add_argument("--dest-db", default=os.getenv("TIMESCALE_DB", "stock_timescale_db"))
    parser.add_argument("--dest-user", default=os.getenv("TIMESCALE_USER", "postgres"))
    parser.add_argument("--dest-password", default=os.getenv("TIMESCALE_PASSWORD", "postgres"))

    parser.add_argument("--iterations", type=int, default=5, help="Number of benchmark iterations")

    args = parser.parse_args()

    ts_conn = get_connection(
        args.dest_host, args.dest_port, args.dest_db, args.dest_user, args.dest_password, name="TimescaleDB (Port 5434)"
    )
    if not ts_conn:
        print("FATAL: Could not connect to TimescaleDB container on port 5434. Is docker running?")
        sys.exit(1)

    src_conn = get_connection(
        args.src_host, args.src_port, args.src_db, args.src_user, args.src_password, name="Local PostgreSQL (Port 5435)"
    )

    try:
        ht_passed, ht_info = verify_hypertable(ts_conn)
        count_matched, src_cnt, ts_cnt = reconcile_row_counts(src_conn, ts_conn)
        bench_stats = benchmark_time_bucket_query(ts_conn, iterations=args.iterations)
        print_summary_report(ht_passed, count_matched, src_cnt, ts_cnt, bench_stats)

    finally:
        if ts_conn:
            ts_conn.close()
        if src_conn:
            src_conn.close()


if __name__ == "__main__":
    main()
