#!/usr/bin/env python3
"""
TimescaleDB Migration Script for Historical Stock Price Data.

Extracts time-series stock price records from local PostgreSQL (port 5432, stock_market_db)
and bulk-inserts them into TimescaleDB (port 5433, stock_timescale_db) into a hypertable
named `stock_price_history`.
"""

import os
import sys
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values


def get_source_connection(host, port, dbname, user, password):
    """Connects to local PostgreSQL on port 5432."""
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
        print("  [✓] Connected to source PostgreSQL successfully.")
        return conn
    except Exception as e:
        print(f"  [✗] Failed to connect to source PostgreSQL: {e}", file=sys.stderr)
        raise


def get_dest_connection(host, port, dbname, user, password):
    """Connects to TimescaleDB on port 5433."""
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
    Ensures TimescaleDB extension is enabled, creates the table
    stock_price_history, and converts it into a hypertable.
    """
    print("\nInitializing TimescaleDB hypertable schema...")
    with dest_conn.cursor() as cur:
        # 1. Enable extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

        # 2. Create stock_price_history table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_price_history (
            ticker VARCHAR(20) NOT NULL,
            price_date TIMESTAMPTZ NOT NULL,
            open_price NUMERIC(14,4),
            high_price NUMERIC(14,4),
            low_price NUMERIC(14,4),
            close_price NUMERIC(14,4),
            volume BIGINT,
            PRIMARY KEY (ticker, price_date)
        );
        """
        cur.execute(create_table_sql)

        # 3. Create hypertable
        cur.execute("SELECT create_hypertable('stock_price_history', 'price_date', if_not_exists => TRUE);")
        res = cur.fetchall()
        print(f"  [✓] Table 'stock_price_history' ready.")
        status_msg = res[0][0] if res and res[0] else "already exists or created"
        print(f"  [✓] Hypertable configured (status: {status_msg}).")

    dest_conn.commit()


def extract_and_migrate_data(src_conn, dest_conn, batch_size=10000):
    """
    Extracts historical stock prices from daily_price_history on port 5432
    and bulk-inserts them into stock_price_history on port 5433 using ON CONFLICT DO NOTHING.
    """
    print("\nExtracting historical stock prices from local PostgreSQL (port 5432)...")
    start_time = datetime.now()

    # Query source row count
    with src_conn.cursor() as count_cur:
        count_cur.execute("SELECT count(*) FROM daily_price_history;")
        src_total = count_cur.fetchone()[0]
        print(f"  Found {src_total:,} records in source table 'daily_price_history'.")
        if src_total == 0:
            print("  [!] Warning: Source table 'daily_price_history' contains 0 rows.")
            print("      Run the data ingestion script first if you have not loaded CSV records:")
            print("      python scripts/ingest_data.py --port 5432")
            return 0

    select_sql = """
    SELECT ticker,
           trading_date::timestamptz AS price_date,
           open_price,
           high_price,
           low_price,
           close_price,
           volume
    FROM daily_price_history
    ORDER BY trading_date ASC;
    """

    insert_sql = """
    INSERT INTO stock_price_history (
        ticker,
        price_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume
    ) VALUES %s
    ON CONFLICT (ticker, price_date) DO NOTHING;
    """

    total_extracted = 0
    total_inserted = 0

    # Use server-side cursor to stream records efficiently
    with src_conn.cursor(name="src_price_cursor") as src_cur:
        src_cur.itersize = batch_size
        src_cur.execute(select_sql)

        with dest_conn.cursor() as dest_cur:
            while True:
                rows = src_cur.fetchmany(batch_size)
                if not rows:
                    break

                total_extracted += len(rows)

                # Bulk insert using execute_values for high throughput
                execute_values(
                    dest_cur,
                    insert_sql,
                    rows,
                    template="(%s, %s, %s, %s, %s, %s, %s)",
                    page_size=batch_size
                )
                dest_conn.commit()
                total_inserted += len(rows)
                pct = (total_inserted / src_total) * 100 if src_total > 0 else 100
                print(f"  - Progress: {total_inserted:,} / {src_total:,} records synced ({pct:.1f}%)...", end="\r")

    duration = (datetime.now() - start_time).total_seconds()
    print(f"\n  [✓] Bulk migration completed: {total_inserted:,} records synced in {duration:.2f}s.")
    return total_inserted


def verify_hypertable_status(dest_conn):
    """
    Verifies hypertable configuration, chunks, and record count in TimescaleDB.
    """
    print("\nVerifying TimescaleDB Hypertable Status:")
    print("=" * 65)
    with dest_conn.cursor() as cur:
        # Row count
        cur.execute("SELECT count(*) FROM stock_price_history;")
        total_records = cur.fetchone()[0]

        # Hypertable catalog info
        cur.execute("""
        SELECT hypertable_schema,
               hypertable_name,
               num_chunks,
               compression_enabled
        FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'stock_price_history';
        """)
        ht_info = cur.fetchone()

        # Chunk range info
        cur.execute("""
        SELECT count(*),
               COALESCE(min(range_start)::text, 'N/A'),
               COALESCE(max(range_end)::text, 'N/A')
        FROM timescaledb_information.chunks
        WHERE hypertable_name = 'stock_price_history';
        """)
        chunk_info = cur.fetchone()

        print(f"Hypertable Name      : {ht_info[1] if ht_info else 'stock_price_history'}")
        print(f"Schema               : {ht_info[0] if ht_info else 'public'}")
        print(f"Total Rows Synced    : {total_records:,}")
        print(f"Active Chunks        : {chunk_info[0] if chunk_info else 0}")
        if chunk_info and chunk_info[0] > 0:
            print(f"Chunk Date Span      : {chunk_info[1]}  --->  {chunk_info[2]}")
        print(f"Compression Enabled  : {ht_info[3] if ht_info else 'False'}")
        print("=" * 65)
        print("TIMESCALEDB HYPERTABLE VERIFICATION SUCCESSFUL!")


def main():
    parser = argparse.ArgumentParser(description="Migrate historical stock data from PostgreSQL 5432 to TimescaleDB 5433.")

    # Source PostgreSQL (5432)
    parser.add_argument("--src-host", default=os.getenv("SRC_PGHOST", os.getenv("PGHOST", "localhost")))
    parser.add_argument("--src-port", type=int, default=int(os.getenv("SRC_PGPORT", os.getenv("PGPORT", "5432"))))
    parser.add_argument("--src-db", default=os.getenv("SRC_PGDATABASE", os.getenv("PGDATABASE", "stock_market_db")))
    parser.add_argument("--src-user", default=os.getenv("SRC_PGUSER", os.getenv("PGUSER", "postgres")))
    parser.add_argument("--src-password", default=os.getenv("SRC_PGPASSWORD", os.getenv("PGPASSWORD", "postgres")))

    # Target TimescaleDB (5433)
    parser.add_argument("--dest-host", default=os.getenv("DEST_PGHOST", "localhost"))
    parser.add_argument("--dest-port", type=int, default=int(os.getenv("DEST_PGPORT", "5433")))
    parser.add_argument("--dest-db", default=os.getenv("DEST_PGDATABASE", "stock_timescale_db"))
    parser.add_argument("--dest-user", default=os.getenv("DEST_PGUSER", "postgres"))
    parser.add_argument("--dest-password", default=os.getenv("DEST_PGPASSWORD", "postgres"))

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
        verify_hypertable_status(dest_conn)

    finally:
        if src_conn:
            src_conn.close()
        if dest_conn:
            dest_conn.close()


if __name__ == "__main__":
    main()
