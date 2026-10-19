# DBS – Stock Market Analytics and Portfolio Management System

A relational database project built on **PostgreSQL 18** that models 25 years of historical price data for Nifty 50 stocks, paired with a portfolio management schema covering holdings, transactions, watchlists, alerts, risk analysis, and ML predictions.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Database Schema](#database-schema)
- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Data Ingestion](#data-ingestion)
- [Running SQL Scripts and Views](#running-sql-scripts-and-views)
- [Running Tests](#running-tests)
- [Dataset](#dataset)
- [ER Diagrams](#er-diagrams)
- [Documentation](#documentation)

---

## Project Overview

This project implements a fully normalized relational database for stock market analytics and portfolio tracking. It ingests real-world Nifty 50 historical data (1999–2026) sourced from Yahoo Finance, and provides a rich SQL query library covering joins, aggregations, window functions, correlated subqueries, views, stored procedures, and triggers.

The system is designed as a collaborative academic and engineering reference for database systems (DBS) coursework.

---

## Features

- **13-table relational schema** — market data, portfolio management, risk analysis, and ML prediction tables with full referential integrity and optimized indexes.
- **287,310 daily price records** across 49 Nifty 50 companies (1999–2026).
- **1,653 corporate action events** — 1,555 dividends and 98 stock splits with uniqueness constraints.
- **6 analytical views** covering latest prices, fundamentals, performance rankings, sector aggregates, volatility, and corporate action summaries.
- **7 stored procedures** for portfolio operations: buying, selling, calculating portfolio value and profit/loss, and watchlist retrieval.
- **2 database triggers**:
  - `trg_portfolio_transaction_audit` — full audit ledger capturing INSERT, UPDATE, DELETE on all portfolio transactions.
  - `trg_portfolio_transaction_consistency` — enforces accurate sell limits, cross-user holding isolation, and row-level concurrency locking.
- **10-file analytical query suite** — basic queries, joins, aggregations, subqueries, correlated subqueries, window functions, stock performance, sector analysis, volatility analysis, and corporate actions.
- **Atomic CSV ingestion pipeline** (`scripts/ingest_data.py`) — loads 288,963 records in ~1.52 seconds via native PostgreSQL `COPY`.
- **Trigger test suite** with 8 functional tests plus a live multi-threaded race condition test, all passing.

---

## Repository Structure

```
DBS-Stock-Market-Analytics/
├── .env.example                        # PostgreSQL connection template (copy to .env)
├── data/
│   ├── historical/
│   │   └── nifty50_historical_data.csv      # 287,310 daily price records (84 MB)
│   ├── processed/
│   │   └── nifty50_summary_statistics.csv   # 49-row per-company summary statistics
│   └── metadata/
│       └── metadata.json                    # Dataset metadata (source, columns, period)
├── docs/
│   ├── database-design/
│   │   ├── schema-proposal.md          # Full table specifications & design rationale
│   │   ├── ingestion-plan.md           # Ingestion execution report & validation results
│   │   ├── triggers.md                 # Trigger specification, audit design & test results
│   │   ├── final-review.md             # Pre-implementation audit & status report
│   │   └── final-design-review.md
│   └── er-diagram/
│       └── *.jpeg                      # Hand-drawn ER diagram sheets (3 pages)
├── scripts/
│   ├── ingest_data.py                  # CSV → PostgreSQL ingestion pipeline
│   ├── test_queries.py                 # Analytical SQL query test runner
│   └── test_triggers.py               # Trigger & concurrency regression test runner
├── sql/
│   ├── schema/
│   │   └── 01_create_schema.sql        # DDL: all 13 tables, indexes
│   ├── views/
│   │   ├── 01_v_latest_stock_prices.sql
│   │   ├── 02_v_company_fundamentals.sql
│   │   ├── 03_v_stock_performance.sql
│   │   ├── 04_v_sector_performance.sql
│   │   ├── 05_v_stock_volatility.sql
│   │   └── 06_v_corporate_action_summary.sql
│   ├── procedures/
│   │   ├── 01_get_latest_stock_price.sql
│   │   ├── 02_get_stock_history.sql
│   │   ├── 03_calculate_portfolio_value.sql
│   │   ├── 04_calculate_portfolio_profit_loss.sql
│   │   ├── 05_get_watchlist_with_prices.sql
│   │   ├── 06_record_stock_purchase.sql
│   │   └── 07_record_stock_sale.sql
│   ├── triggers/
│   │   ├── 01_portfolio_transaction_audit.sql
│   │   └── 02_portfolio_consistency.sql
│   └── queries/
│       ├── 01_basic_queries.sql
│       ├── 02_joins.sql
│       ├── 03_aggregations_group_by.sql
│       ├── 04_subqueries.sql
│       ├── 05_correlated_subqueries.sql
│       ├── 06_window_functions.sql
│       ├── 07_stock_performance.sql
│       ├── 08_sector_analysis.sql
│       ├── 09_volatility_analysis.sql
│       └── 10_corporate_actions.sql
└── tests/
    ├── test_triggers.sql               # SQL trigger integration test suite (8 scenarios)
    └── test_portfolio_lifecycle.sql    # Portfolio lifecycle & stock sale regression tests
```

---

## Database Schema

The schema comprises **13 tables** across two domains:

**Market Data** (populated by ingestion pipeline):

| Table | Rows | Description |
|---|---|---|
| `sector` | 13 | Industry classifications |
| `company` | 49 | Nifty 50 constituent companies |
| `daily_price_history` | 287,310 | Daily OHLCV + technical indicators (1999–2026) |
| `corporate_action` | 1,653 | Dividend and stock split events |
| `current_fundamentals` | 49 | Latest per-company valuation metrics (2026-01-30 snapshot) |
| `stock_summary` | 49 | Long-term aggregate statistics per company |

**Application / Portfolio** (populated by application use):

| Table | Description |
|---|---|
| `app_user` | User accounts with role-based access |
| `user_watchlist` | Per-user ticker watchlists with alert price thresholds |
| `portfolio_holding` | Aggregated investment positions per user |
| `portfolio_transaction` | Full BUY / SELL / DIVIDEND / SPLIT ledger |
| `alert` | System and price threshold notifications |
| `portfolio_risk_analysis` | Per-user computed risk metrics (Sharpe ratio, volatility, max drawdown) |
| `ml_prediction` | Machine learning price forecasts per ticker |

See [`docs/database-design/schema-proposal.md`](docs/database-design/schema-proposal.md) for full column-level specifications.

---

## Prerequisites

- **PostgreSQL 18** (tested on PostgreSQL 18.4)
- **Python 3.8+** (standard library only — no additional packages required)
- `psql` CLI available in your `PATH`

> The Python ingestion and test scripts use only the Python standard library (`os`, `sys`, `csv`, `subprocess`, `argparse`, `threading`). No `pip install` step is required.

---

## Environment Configuration

The scripts read PostgreSQL connection parameters from environment variables with built-in defaults. To configure your local environment:

```bash
cp .env.example .env
# Edit .env and set PGUSER to your local PostgreSQL role name
```

**`.env.example` reference:**

```
PGHOST=localhost
PGPORT=5435
PGDATABASE=stock_market_db
PGUSER=your_postgres_username
```

> `.env` is git-ignored and will never be committed. Do not store passwords in any tracked file.

If you use a password-protected PostgreSQL role, configure `~/.pgpass` or set `PGPASSWORD` in your shell session (never commit it).

---

## Database Setup

**Step 1 — Create the database:**

```bash
createdb -h localhost -p 5435 -U your_postgres_username stock_market_db
```

**Step 2 — Run the DDL migration (creates all 13 tables and indexes):**

```bash
psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db \
     -f sql/schema/01_create_schema.sql
```

**Step 3 — Apply views:**

```bash
for f in sql/views/*.sql; do
  psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db -f "$f"
done
```

**Step 4 — Apply stored procedures:**

```bash
for f in sql/procedures/*.sql; do
  psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db -f "$f"
done
```

**Step 5 — Apply triggers:**

```bash
for f in sql/triggers/*.sql; do
  psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db -f "$f"
done
```

---

## Data Ingestion

The ingestion script loads both CSV datasets into the database inside a single atomic PostgreSQL `COPY` transaction. It validates preconditions before loading and runs comprehensive post-load verification automatically.

**Run ingestion:**

```bash
python3 scripts/ingest_data.py \
  --host localhost \
  --port 5435 \
  --dbname stock_market_db \
  --user your_postgres_username
```

The script accepts the same parameters as environment variable overrides:

| Argument | Default (`os.getenv` fallback) | Description |
|---|---|---|
| `--host` | `PGHOST` → `localhost` | PostgreSQL host |
| `--port` | `PGPORT` → `5435` | PostgreSQL port |
| `--dbname` | `PGDATABASE` → `stock_market_db` | Database name |
| `--user` | `PGUSER` → `easwarap` | PostgreSQL role |
| `--historical-csv` | `data/historical/nifty50_historical_data.csv` | Historical price data path |
| `--summary-csv` | `data/processed/nifty50_summary_statistics.csv` | Summary statistics path |
| `--verify-only` | — | Skip ingestion; run validation queries only |

**Expected output (on success):**

```
Connected to database 'stock_market_db' as user '...' on port 5435.
Confirmed all 13 expected tables exist.
Confirmed all 6 market-data tables are currently empty (0 rows).
Prepared records:
  - sector: 13 rows
  - company: 49 rows
  - daily_price_history: 287310 rows
  - corporate_action: 1653 rows
  - current_fundamentals: 49 rows
  - stock_summary: 49 rows
Executing ingestion inside an atomic transaction via psql COPY...
Ingestion transaction completed successfully in 1.52 seconds.
ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!
```

---

## Running SQL Scripts and Views

Run any individual SQL file directly with `psql`:

```bash
# Example: run a specific analytical query file
psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db \
     -f sql/queries/06_window_functions.sql

# Example: query through a view
psql -h localhost -p 5435 -U your_postgres_username -d stock_market_db \
     -c "SELECT * FROM v_latest_stock_prices LIMIT 10;"
```

The analytical query test runner executes all 10 files in `sql/queries/` and reports pass/fail per file:

```bash
python3 scripts/test_queries.py
```

---

## Running Tests

**Trigger integration and regression tests** (SQL suite + live multi-threaded concurrency test):

```bash
python3 scripts/test_triggers.py
```

This runs:
1. Trigger catalog verification (confirms both triggers are enabled in PostgreSQL)
2. `tests/test_triggers.sql` — 8 functional trigger scenarios
3. `tests/test_portfolio_lifecycle.sql` — portfolio lifecycle and stock sale regression tests
4. A live multi-threaded race condition test (two concurrent sessions competing on the same holding)
5. Database cleanliness check (confirms 0 residual test rows)
6. Market data integrity check (confirms row counts unchanged)

All 9 test scenarios (8 SQL + 1 live concurrent) were verified passing. See [`docs/database-design/triggers.md`](docs/database-design/triggers.md) for the full test results table.

---

## Dataset

| File | Size | Records | Source |
|---|---|---|---|
| `data/historical/nifty50_historical_data.csv` | ~84 MB | 287,310 rows | Yahoo Finance |
| `data/processed/nifty50_summary_statistics.csv` | ~16 KB | 49 rows | Derived from historical data |

**Coverage:** 49 Nifty 50 constituent companies across 13 sectors, daily records from 1999-01-01 to 2026-01-31.

**Columns:** Date, Ticker, Company Name, Sector, Open, High, Low, Close, Volume, Dividend, Stock Split, Daily Return, Volatility (20D), MA-50, MA-200, Market Cap, PE Ratio, Forward PE, PEG Ratio, Price-to-Book, Dividend Yield, EPS, Beta, 52-Week High, 52-Week Low.

> **Note on negative adjusted prices:** 47 rows for `ADANIENT.NS` (2002-07-01 to 2002-09-03) contain slightly negative close prices (–0.0122 to –0.0107). This is a known mathematical artifact of Yahoo Finance's backward dividend adjustment applied to a very low split-adjusted nominal price (~₹0.05). These records are preserved unaltered in the database. See [`docs/database-design/schema-proposal.md`](docs/database-design/schema-proposal.md) for the full explanation.

---

## ER Diagrams

Hand-drawn ER diagrams are included in [`docs/er-diagram/`](docs/er-diagram/):

- **Sheet 1** — Market data entities: `company`, `daily_price_history`, `corporate_action`, `current_fundamentals`, `stock_summary`, `ml_prediction`
- **Sheet 2** — Application entities: `app_user`, `user_watchlist`, `portfolio_holding`, `portfolio_transaction`, `alert`, `portfolio_risk_analysis`
- **Sheet 3** — Sector classification and cross-domain relationships

---

## Documentation

| Document | Description |
|---|---|
| [`docs/database-design/schema-proposal.md`](docs/database-design/schema-proposal.md) | Full table specifications, design decisions, and foreign key strategy |
| [`docs/database-design/ingestion-plan.md`](docs/database-design/ingestion-plan.md) | Ingestion execution report with row counts and integrity validation results |
| [`docs/database-design/triggers.md`](docs/database-design/triggers.md) | Trigger architecture, audit design review, catalog verification, and test results |
| [`docs/database-design/final-review.md`](docs/database-design/final-review.md) | Pre-implementation audit resolving all dataset discrepancies |
