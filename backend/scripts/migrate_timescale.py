#!/usr/bin/env python3
"""
TimescaleDB Migration Script for Historical Stock Price Data.

Safely extracts historical stock price records from local PostgreSQL (port 5435, stock_market_db)
and bulk-inserts them into TimescaleDB (port 5434, stock_timescale_db) into a hypertable
named `daily_price_history`.

Preserves all 11 source columns and exact DATE semantics:
- ticker
- trading_date
- open_price
- high_price
- low_price
- close_price
- volume
- daily_return
- vol_20d
- ma_50
- ma_200

Features:
- Idempotent execution via ON CONFLICT (ticker, trading_date) DO NOTHING.
- Server-side cursor for efficient streaming memory management.
- Batch inserts with execute_values for high throughput.
- Accurate inserted, skipped, conflicting, and failed row reporting.
- Strict read-only posture towards source database.
- Full reconciliation verification (row counts, date ranges, ticker counts, representative samples).
"""

import os
import sys
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load .env from project root
_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(_env_path)


def get_source_connection(host, port, dbname, user, password):
    """Connects to source PostgreSQL (read-only)."""
    print(f"Connecting to source PostgreSQL at {host}:{port}/{dbname} as '{user}'...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10
        )
        conn.set_session(readonly=True)
        print("  [✓] Connected to source PostgreSQL successfully (read-only mode).")
        return conn
    except Exception as e:
        print(f"  [✗] Failed to connect to source PostgreSQL: {e}", file=sys.stderr)
        raise


def get_dest_connection(host, port, dbname, user, password):
    """Connects to target TimescaleDB."""
    print(f"Connecting to target TimescaleDB at {host}:{port}/{dbname} as '{user}'...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10
        )
        print("  [✓] Connected to target TimescaleDB successfully.")
        return conn
    except Exception as e:
        print(f"  [✗] Failed to connect to target TimescaleDB: {e}", file=sys.stderr)
        raise


def setup_timescaledb_hypertable(dest_conn):
    """
    Ensures TimescaleDB extension is enabled, creates table daily_price_history,
    converts it into a hypertable partitioned on trading_date, and creates supporting indexes
    and compatibility view stock_price_history.
    """
    print("\n[Step 1] Ensuring TimescaleDB Hypertable Schema...")
    with dest_conn.cursor() as cur:
        # 1. Enable extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

        # 2. Create daily_price_history table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_price_history (
            ticker TEXT NOT NULL,
            trading_date DATE NOT NULL,
            open_price NUMERIC(14,4),
            high_price NUMERIC(14,4),
            low_price NUMERIC(14,4),
            close_price NUMERIC(14,4),
            volume BIGINT CHECK (volume >= 0),
            daily_return NUMERIC(10,4),
            vol_20d NUMERIC(10,4),
            ma_50 NUMERIC(14,4),
            ma_200 NUMERIC(14,4),
            PRIMARY KEY (ticker, trading_date)
        );
        """)

        # 3. Create hypertable on trading_date
        cur.execute("SELECT create_hypertable('daily_price_history', 'trading_date', if_not_exists => TRUE);")
        ht_res = cur.fetchall()

        # 4. Create supporting indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dph_trading_date ON daily_price_history (trading_date DESC);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dph_ticker_date ON daily_price_history (ticker, trading_date DESC);")

        # 5. Create compatibility view for queries using stock_price_history
        cur.execute("""
        CREATE OR REPLACE VIEW stock_price_history AS
        SELECT ticker,
               trading_date,
               trading_date::timestamptz AS price_date,
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

    dest_conn.commit()
    print("  [✓] Hypertable 'daily_price_history' ready and indexes created.")


def extract_and_migrate_data(src_conn, dest_conn, batch_size=10000):
    """
    Streams historical stock prices from PostgreSQL daily_price_history
    and inserts them into TimescaleDB daily_price_history using ON CONFLICT DO NOTHING.
    Tracks exact counts of inserted, skipped, and processed records.
    """
    print("\n[Step 2] Migrating Historical Price Data...")
    start_time = datetime.now()

    # Query source count
    with src_conn.cursor() as count_cur:
        count_cur.execute("SELECT COUNT(*) FROM daily_price_history;")
        src_total = count_cur.fetchone()[0]
        print(f"  Found {src_total:,} records in source table 'daily_price_history'.")
        if src_total == 0:
            print("  [!] Warning: Source table is empty. Nothing to migrate.")
            return 0, 0, 0

    select_sql = """
    SELECT ticker,
           trading_date,
           open_price,
           high_price,
           low_price,
           close_price,
           volume,
           daily_return,
           vol_20d,
           ma_50,
           ma_200
    FROM daily_price_history
    ORDER BY trading_date ASC, ticker ASC;
    """

    insert_sql = """
    INSERT INTO daily_price_history (
        ticker,
        trading_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        daily_return,
        vol_20d,
        ma_50,
        ma_200
    ) VALUES %s
    ON CONFLICT (ticker, trading_date) DO NOTHING;
    """

    total_extracted = 0
    total_inserted = 0
    total_skipped = 0

    with src_conn.cursor(name="src_price_stream_cursor") as src_cur:
        src_cur.itersize = batch_size
        src_cur.execute(select_sql)

        with dest_conn.cursor() as dest_cur:
            while True:
                rows = src_cur.fetchmany(batch_size)
                if not rows:
                    break

                batch_len = len(rows)
                total_extracted += batch_len

                execute_values(
                    dest_cur,
                    insert_sql,
                    rows,
                    template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    page_size=batch_size
                )
                dest_conn.commit()

                # rowcount reflects rows actually inserted vs skipped due to ON CONFLICT
                batch_inserted = dest_cur.rowcount
                batch_skipped = batch_len - batch_inserted
                total_inserted += batch_inserted
                total_skipped += batch_skipped

                pct = (total_extracted / src_total) * 100 if src_total > 0 else 100
                print(
                    f"  - Progress: {total_extracted:,} / {src_total:,} rows ({pct:.1f}%) "
                    f"[Inserted: {total_inserted:,} | Skipped: {total_skipped:,}]...",
                    end="\r"
                )

    duration = (datetime.now() - start_time).total_seconds()
    print(
        f"\n  [✓] Migration batch loop completed in {duration:.2f}s."
        f"\n      Extracted: {total_extracted:,}"
        f"\n      Inserted : {total_inserted:,}"
        f"\n      Skipped  : {total_skipped:,} (conflicting/pre-existing)"
    )
    return total_extracted, total_inserted, total_skipped


def reconcile_data(src_conn, dest_conn):
    """
    Verifies reconciliation between source PostgreSQL and destination TimescaleDB:
    - Row count
    - Min & Max date
    - Distinct ticker count
    - Representative sample records across both databases
    - TimescaleDB hypertable chunks and date span
    """
    print("\n[Step 3] Reconciling Source and Destination Data...")
    print("=" * 70)

    # 1. Source Stats
    with src_conn.cursor() as cur:
        cur.execute("""
        SELECT COUNT(*),
               MIN(trading_date)::text,
               MAX(trading_date)::text,
               COUNT(DISTINCT ticker)
        FROM daily_price_history;
        """)
        src_cnt, src_min, src_max, src_tickers = cur.fetchone()

    # 2. Destination Stats
    with dest_conn.cursor() as cur:
        cur.execute("""
        SELECT COUNT(*),
               MIN(trading_date)::text,
               MAX(trading_date)::text,
               COUNT(DISTINCT ticker)
        FROM daily_price_history;
        """)
        dest_cnt, dest_min, dest_max, dest_tickers = cur.fetchone()

        # Hypertable chunks
        cur.execute("""
        SELECT COUNT(*),
               COALESCE(MIN(range_start)::text, 'N/A'),
               COALESCE(MAX(range_end)::text, 'N/A')
        FROM timescaledb_information.chunks
        WHERE hypertable_name = 'daily_price_history';
        """)
        chunks_info = cur.fetchone()

    print(f"{'Metric':<25} | {'Source (PostgreSQL 5435)':<20} | {'Dest (TimescaleDB 5434)':<20}")
    print("-" * 70)
    print(f"{'Row Count':<25} | {src_cnt:<20,} | {dest_cnt:<20,}")
    print(f"{'Earliest Date':<25} | {src_min:<20} | {dest_min:<20}")
    print(f"{'Latest Date':<25} | {src_max:<20} | {dest_max:<20}")
    print(f"{'Distinct Tickers':<25} | {src_tickers:<20} | {dest_tickers:<20}")
    print("-" * 70)
    print(f"TimescaleDB Chunks        : {chunks_info[0]} active chunk(s)")
    print(f"Chunk Date Boundaries     : {chunks_info[1]}  --->  {chunks_info[2]}")
    print("=" * 70)

    # Validation checks
    assert src_cnt == dest_cnt, f"Row count mismatch! Source: {src_cnt}, Dest: {dest_cnt}"
    assert src_min == dest_min, f"Min date mismatch! Source: {src_min}, Dest: {dest_min}"
    assert src_max == dest_max, f"Max date mismatch! Source: {src_max}, Dest: {dest_max}"
    assert src_tickers == dest_tickers, f"Ticker count mismatch! Source: {src_tickers}, Dest: {dest_tickers}"

    # Sample verification on key tickers
    sample_tickers = ["TCS.NS", "RELIANCE.NS", "INFY.NS", "HDFCBANK.NS", "ITC.NS"]
    print("\n[Step 4] Spot-Checking Representative Records (Latest Trading Day 2026-01-30)...")
    for t in sample_tickers:
        with src_conn.cursor() as s_cur:
            s_cur.execute(
                "SELECT ticker, trading_date::text, close_price, volume, ma_50, ma_200 "
                "FROM daily_price_history WHERE ticker = %s AND trading_date = '2026-01-30';",
                (t,)
            )
            s_row = s_cur.fetchone()

        with dest_conn.cursor() as d_cur:
            d_cur.execute(
                "SELECT ticker, trading_date::text, close_price, volume, ma_50, ma_200 "
                "FROM daily_price_history WHERE ticker = %s AND trading_date = '2026-01-30';",
                (t,)
            )
            d_row = d_cur.fetchone()

        assert s_row == d_row, f"Sample mismatch for {t}!\n  Source: {s_row}\n  Dest:   {d_row}"
        print(f"  [✓] Verified {t}: close={d_row[2]}, vol={d_row[3]}, ma50={d_row[4]}, ma200={d_row[5]}")

    print("\n[✓] ALL RECONCILIATION CHECKS PASSED PERFECTLY!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate historical stock data from PostgreSQL 5435 to TimescaleDB 5434.")

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

    parser.add_argument("--batch-size", type=int, default=10000, help="Batch size for bulk insertion")

    args = parser.parse_args()

    src_conn = None
    dest_conn = None
    try:
        dest_conn = get_dest_connection(
            args.dest_host, args.dest_port, args.dest_db, args.dest_user, args.dest_password
        )
        setup_timescaledb_hypertable(dest_conn)

        src_conn = get_source_connection(
            args.src_host, args.src_port, args.src_db, args.src_user, args.src_password
        )

        extract_and_migrate_data(src_conn, dest_conn, batch_size=args.batch_size)
        reconcile_data(src_conn, dest_conn)

    except Exception as e:
        print(f"\n[FATAL] Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if src_conn:
            src_conn.close()
        if dest_conn:
            dest_conn.close()


if __name__ == "__main__":
    main()
