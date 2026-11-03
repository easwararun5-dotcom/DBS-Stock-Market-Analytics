#!/usr/bin/env python3
"""
Reproducible CSV Data Ingestion Pipeline for stock_market_db.

Loads and cleans financial datasets into PostgreSQL 18:
1. sector (13 rows)
2. company (49 rows)
3. daily_price_history (287,310 rows)
4. corporate_action (1,653 rows)
5. current_fundamentals (49 rows)
6. stock_summary (49 rows)

Strict referential integrity, atomic transaction, and zero fabricated application records.
"""

import os
import sys
import csv
import argparse
import subprocess
from datetime import datetime
from collections import OrderedDict


def clean_val(val):
    """Return '\\N' for empty/whitespace string, else cleaned string."""
    if val is None:
        return r"\N"
    s = str(val).strip()
    return r"\N" if s == "" else s


def clean_date(date_str):
    """Extract YYYY-MM-DD from timestamp string."""
    if not date_str:
        return r"\N"
    return date_str.strip()[:10]


def run_psql_query(psql_cmd, query):
    """Execute a query and return standard output."""
    res = subprocess.run(
        psql_cmd + ["-t", "-A", "-c", query],
        capture_output=True,
        text=True,
        check=True
    )
    return res.stdout.strip()


def check_preconditions(psql_cmd):
    """Verify that all 13 tables exist and 6 market data tables are empty."""
    print("Checking database connection and pre-load state...")
    
    # Check current db and user
    ident = run_psql_query(psql_cmd, "SELECT current_database() || '|' || current_user || '|' || inet_server_port();")
    db, user, port = ident.split("|")
    print(f"Connected to database '{db}' as user '{user}' on port {port}.")

    # Check 13 expected tables
    tables_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """
    tables = run_psql_query(psql_cmd, tables_query).splitlines()
    tables = [t.strip() for t in tables if t.strip()]
    
    expected_tables = {
        'sector', 'company', 'daily_price_history', 'corporate_action',
        'current_fundamentals', 'stock_summary', 'app_user', 'user_watchlist',
        'portfolio_holding', 'portfolio_transaction', 'alert',
        'portfolio_risk_analysis', 'ml_prediction'
    }
    
    if set(tables) != expected_tables:
        missing = expected_tables - set(tables)
        raise RuntimeError(f"Database missing expected tables: {missing}")
    
    print(f"Confirmed all {len(expected_tables)} expected tables exist.")

    # Confirm market-data tables are empty
    market_tables = ['sector', 'company', 'daily_price_history', 'corporate_action', 'current_fundamentals', 'stock_summary']
    for tbl in market_tables:
        cnt = int(run_psql_query(psql_cmd, f"SELECT count(*) FROM {tbl};"))
        if cnt > 0:
            raise RuntimeError(f"Pre-condition failed: table '{tbl}' is not empty (contains {cnt} rows).")
            
    print("Confirmed all 6 market-data tables are currently empty (0 rows).")


def build_ingestion_stream(historical_path, summary_path):
    """
    Read CSVs, apply transformation rules, and generate COPY commands and data streams.
    Returns (sql_commands_text, stream_bytes).
    """
    print(f"Reading historical dataset: {historical_path}")
    print(f"Reading summary dataset: {summary_path}")

    sectors = OrderedDict()
    companies = OrderedDict()
    price_records = []
    corp_action_records = []
    latest_fundamentals = {}

    # 1. Parse historical data
    with open(historical_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ticker = r["Ticker"].strip()
            cname = r["Company_Name"].strip()
            sec = r["Sector"].strip()
            date = clean_date(r["Date"])

            if sec and sec not in sectors:
                sectors[sec] = len(sectors) + 1  # 1-indexed

            if ticker not in companies:
                companies[ticker] = (cname, sec)

            # Daily price history
            open_p = clean_val(r.get("Open"))
            high_p = clean_val(r.get("High"))
            low_p = clean_val(r.get("Low"))
            close_p = clean_val(r.get("Close"))
            vol = clean_val(r.get("Volume"))
            ret = clean_val(r.get("Daily_Return"))
            vol20 = clean_val(r.get("Volatility_20D"))
            ma50 = clean_val(r.get("MA_50"))
            ma200 = clean_val(r.get("MA_200"))

            price_records.append(f"{ticker}\t{date}\t{open_p}\t{high_p}\t{low_p}\t{close_p}\t{vol}\t{ret}\t{vol20}\t{ma50}\t{ma200}\n")

            # Corporate actions (non-zero events)
            div_str = r.get("Dividend", "").strip()
            if div_str and float(div_str) > 0:
                corp_action_records.append(f"{ticker}\t{date}\tDividend\t{div_str}\n")

            split_str = r.get("Stock_Split", "").strip()
            if split_str and float(split_str) > 0:
                corp_action_records.append(f"{ticker}\t{date}\tStock_Split\t{split_str}\n")

            # Update latest fundamentals snapshot (chronologically last occurrence)
            latest_fundamentals[ticker] = r

    # 2. Parse summary dataset
    summary_records = []
    with open(summary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            sec = r["Sector"].strip()
            if sec and sec not in sectors:
                sectors[sec] = len(sectors) + 1

            ticker = r["Ticker"].strip()
            fdate = clean_date(r["First_Date"])
            ldate = clean_date(r["Last_Date"])
            ttd = clean_val(r["Total_Trading_Days"])
            s_price = clean_val(r["Starting_Price"])
            e_price = clean_val(r["Ending_Price"])
            tot_ret = clean_val(r["Total_Return_%"])
            h_price = clean_val(r["Highest_Price"])
            l_price = clean_val(r["Lowest_Price"])
            avg_vol = clean_val(r["Avg_Daily_Volume"])
            tot_div = clean_val(r["Total_Dividends_Paid"])
            num_splits = clean_val(r["Number_of_Splits"])
            avg_ret = clean_val(r["Avg_Daily_Return_%"])
            vol_pct = clean_val(r["Volatility_%"])
            mkt_cap = clean_val(r["Current_Market_Cap"])
            pe = clean_val(r["Current_PE_Ratio"])

            summary_records.append(
                f"{ticker}\t{fdate}\t{ldate}\t{ttd}\t{s_price}\t{e_price}\t{tot_ret}\t{h_price}\t{l_price}\t{avg_vol}\t{tot_div}\t{num_splits}\t{avg_ret}\t{vol_pct}\t{mkt_cap}\t{pe}\n"
            )

    # 3. Format current_fundamentals records
    fundamentals_records = []
    for ticker, r in latest_fundamentals.items():
        date_str = r["Date"].strip()
        snap_year = date_str[:4]  # 2026
        last_updated = clean_date(date_str)

        pe = clean_val(r.get("PE_Ratio"))
        fwd_pe = clean_val(r.get("Forward_PE"))
        ptb = clean_val(r.get("Price_to_Book"))
        div_yield = clean_val(r.get("Dividend_Yield"))
        eps = clean_val(r.get("EPS"))
        beta = clean_val(r.get("Beta"))
        mkt_cap = clean_val(r.get("Market_Cap"))
        peg = clean_val(r.get("PEG_Ratio"))

        fundamentals_records.append(
            f"{ticker}\t{pe}\t{fwd_pe}\t{ptb}\t{div_yield}\t{eps}\t{beta}\t{snap_year}\t{mkt_cap}\t{peg}\t{last_updated}\n"
        )

    # 4. Format sector & company records
    sector_records = [f"{sec}\n" for sec in sectors.keys()]
    
    # Sector name -> assigned SERIAL id (1..N)
    sector_ids = {sec: i for i, sec in enumerate(sectors.keys(), start=1)}
    company_records = [
        f"{ticker}\t{cname}\t{sector_ids[sec]}\n"
        for ticker, (cname, sec) in companies.items()
    ]

    print(f"Prepared records:")
    print(f"  - sector: {len(sector_records)} rows")
    print(f"  - company: {len(company_records)} rows")
    print(f"  - daily_price_history: {len(price_records)} rows")
    print(f"  - corporate_action: {len(corp_action_records)} rows")
    print(f"  - current_fundamentals: {len(fundamentals_records)} rows")
    print(f"  - stock_summary: {len(summary_records)} rows")

    # Build monolithic input script with inline COPY blocks
    stream = []
    stream.append("BEGIN;\n\n")

    # 1. sector
    stream.append("COPY sector (sector_name) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(sector_records)
    stream.append("\\.\n\n")

    # 2. company
    stream.append("COPY company (ticker, company_name, sector_id) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(company_records)
    stream.append("\\.\n\n")

    # 3. daily_price_history
    stream.append("COPY daily_price_history (ticker, trading_date, open_price, high_price, low_price, close_price, volume, daily_return, vol_20d, ma_50, ma_200) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(price_records)
    stream.append("\\.\n\n")

    # 4. corporate_action
    stream.append("COPY corporate_action (ticker, action_date, action_type, action_value) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(corp_action_records)
    stream.append("\\.\n\n")

    # 5. current_fundamentals
    stream.append("COPY current_fundamentals (ticker, pe_ratio, forward_pe, price_to_book, dividend_yield, eps, beta, fiscal_year, market_cap, peg_ratio, last_updated) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(fundamentals_records)
    stream.append("\\.\n\n")

    # 6. stock_summary
    stream.append("COPY stock_summary (ticker, first_trading_date, last_trading_date, total_trading_days, starting_price, ending_price, total_return_pct, highest_price, lowest_price, avg_daily_volume, total_dividends_paid, number_of_splits, avg_daily_return_pct, volatility_pct, current_market_cap, current_pe_ratio) FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
    stream.extend(summary_records)
    stream.append("\\.\n\n")

    stream.append("COMMIT;\n")

    return "".join(stream)


def execute_ingestion(psql_cmd, stream_data):
    """Execute COPY transaction using psql."""
    print("Executing ingestion inside an atomic transaction via psql COPY...")
    start_time = datetime.now()

    proc = subprocess.Popen(
        psql_cmd + ["-v", "ON_ERROR_STOP=1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = proc.communicate(input=stream_data)
    duration = (datetime.now() - start_time).total_seconds()

    if proc.returncode != 0:
        print(f"Ingestion failed with error code {proc.returncode}!")
        print(f"STDERR:\n{stderr}")
        raise RuntimeError(f"Database ingestion transaction failed: {stderr}")

    print(f"Ingestion transaction completed successfully in {duration:.2f} seconds.")


def verify_database(psql_cmd):
    """Run comprehensive post-load verification queries."""
    print("\nRunning post-load validation queries...")
    
    # 1. Exact count verification
    counts_query = """
    SELECT 'sector' AS tbl, count(*), 13 AS expected FROM sector
    UNION ALL SELECT 'company', count(*), 49 FROM company
    UNION ALL SELECT 'daily_price_history', count(*), 287310 FROM daily_price_history
    UNION ALL SELECT 'corporate_action', count(*), 1653 FROM corporate_action
    UNION ALL SELECT 'current_fundamentals', count(*), 49 FROM current_fundamentals
    UNION ALL SELECT 'stock_summary', count(*), 49 FROM stock_summary
    UNION ALL SELECT 'app_user', count(*), 0 FROM app_user
    UNION ALL SELECT 'user_watchlist', count(*), 0 FROM user_watchlist
    UNION ALL SELECT 'portfolio_holding', count(*), 0 FROM portfolio_holding
    UNION ALL SELECT 'portfolio_transaction', count(*), 0 FROM portfolio_transaction
    UNION ALL SELECT 'alert', count(*), 0 FROM alert
    UNION ALL SELECT 'portfolio_risk_analysis', count(*), 0 FROM portfolio_risk_analysis
    UNION ALL SELECT 'ml_prediction', count(*), 0 FROM ml_prediction;
    """
    rows = run_psql_query(psql_cmd, counts_query).splitlines()
    print("\nTable Row Count Verification:")
    print("-" * 55)
    print(f"{'Table':<25} | {'Actual':<10} | {'Expected':<10} | {'Status'}")
    print("-" * 55)

    all_passed = True
    for r in rows:
        tbl, actual, expected = r.split("|")
        act_int = int(actual)
        exp_int = int(expected)
        status = "PASSED" if act_int == exp_int else "FAILED"
        if status == "FAILED":
            all_passed = False
        print(f"{tbl:<25} | {act_int:<10} | {exp_int:<10} | {status}")
    print("-" * 55)

    # 2. Foreign key integrity checks
    fk_queries = {
        "Orphaned Prices": "SELECT count(*) FROM daily_price_history p LEFT JOIN company c ON p.ticker = c.ticker WHERE c.ticker IS NULL;",
        "Orphaned Actions": "SELECT count(*) FROM corporate_action a LEFT JOIN company c ON a.ticker = c.ticker WHERE c.ticker IS NULL;",
        "Orphaned Fundamentals": "SELECT count(*) FROM current_fundamentals f LEFT JOIN company c ON f.ticker = c.ticker WHERE c.ticker IS NULL;",
        "Orphaned Summaries": "SELECT count(*) FROM stock_summary s LEFT JOIN company c ON s.ticker = c.ticker WHERE c.ticker IS NULL;",
        "Orphaned Companies": "SELECT count(*) FROM company c LEFT JOIN sector s ON c.sector_id = s.sector_id WHERE s.sector_id IS NULL;"
    }
    print("\nForeign Key Integrity Checks:")
    for label, q in fk_queries.items():
        cnt = int(run_psql_query(psql_cmd, q))
        status = "PASSED (0 orphans)" if cnt == 0 else f"FAILED ({cnt} orphans)"
        if cnt != 0:
            all_passed = False
        print(f"  - {label:<25}: {status}")

    # 3. Duplicate checks
    dup_prices = int(run_psql_query(psql_cmd, "SELECT count(*) FROM (SELECT ticker, trading_date FROM daily_price_history GROUP BY ticker, trading_date HAVING count(*) > 1) t;"))
    dup_actions = int(run_psql_query(psql_cmd, "SELECT count(*) FROM (SELECT ticker, action_date, action_type FROM corporate_action GROUP BY ticker, action_date, action_type HAVING count(*) > 1) t;"))
    print("\nUniqueness Constraints:")
    print(f"  - Duplicate (ticker, date) in price history: {dup_prices} (Expect: 0)")
    print(f"  - Duplicate (ticker, date, type) in corporate action: {dup_actions} (Expect: 0)")
    if dup_prices != 0 or dup_actions != 0:
        all_passed = False

    # 4. Negative Price Preservation Check
    neg_adani = int(run_psql_query(psql_cmd, "SELECT count(*) FROM daily_price_history WHERE ticker = 'ADANIENT.NS' AND close_price < 0;"))
    neg_total = int(run_psql_query(psql_cmd, "SELECT count(*) FROM daily_price_history WHERE close_price < 0;"))
    print("\nNegative Historical Price Preservation:")
    print(f"  - ADANIENT.NS negative close prices: {neg_adani} rows (Expect: exactly 47)")
    print(f"  - Total negative close prices: {neg_total} rows (Expect: exactly 47)")
    if neg_adani != 47 or neg_total != 47:
        all_passed = False

    # 5. Missing fundamentals check
    peg_nulls = int(run_psql_query(psql_cmd, "SELECT count(*) FROM current_fundamentals WHERE peg_ratio IS NULL;"))
    indusind_pe = run_psql_query(psql_cmd, "SELECT CASE WHEN pe_ratio IS NULL THEN 'NULL' ELSE pe_ratio::text END FROM current_fundamentals WHERE ticker = 'INDUSINDBK.NS';")
    print("\nMissing Fundamentals Preservation:")
    print(f"  - All-NULL peg_ratio count: {peg_nulls} of 49 rows (Expect: 49)")
    print(f"  - INDUSINDBK.NS pe_ratio: {indusind_pe} (Expect: NULL)")
    if peg_nulls != 49 or indusind_pe != "NULL":
        all_passed = False

    if not all_passed:
        raise RuntimeError("Post-load verification checks failed!")

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")


def main():
    parser = argparse.ArgumentParser(description="Ingest CSV datasets into stock_market_db.")
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", default=os.getenv("PGPORT", "5435"))
    parser.add_argument("--dbname", default=os.getenv("PGDATABASE", "stock_market_db"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "easwarap"))
    parser.add_argument("--historical-csv", default="data/historical/nifty50_historical_data.csv")
    parser.add_argument("--summary-csv", default="data/processed/nifty50_summary_statistics.csv")
    parser.add_argument("--verify-only", action="store_true", help="Run validation queries only without ingestion.")

    args = parser.parse_args()

    psql_cmd = ["psql", "-h", args.host, "-p", str(args.port), "-U", args.user, "-d", args.dbname]

    if args.verify_only:
        verify_database(psql_cmd)
        return

    # 1. Preconditions
    check_preconditions(psql_cmd)

    # 2. Build stream
    stream_data = build_ingestion_stream(args.historical_csv, args.summary_csv)

    # 3. Execute
    execute_ingestion(psql_cmd, stream_data)

    # 4. Verify
    verify_database(psql_cmd)


if __name__ == "__main__":
    main()
