# DBS Stock Market Analytics & Portfolio Management System

A production-grade financial analytics and portfolio management web application built as an advanced Database Systems (DBMS) project. Features dual-database architecture (**PostgreSQL** for relational application data and **TimescaleDB** for historical financial time series), a trained machine-learning stock trend prediction pipeline, secure JWT + bcrypt authentication, database-backed portfolio trading with cash accounting and concurrency locking, and a Bloomberg-inspired dark financial UI.

---

## 📊 Dataset & System Summary

| Metric | Specification |
|--------|---------------|
| **Universe** | 49 Indian Blue-Chip Companies (Nifty 50 universe) |
| **Sectors** | 13 Diversified Economic Sectors |
| **Time-Series Engine** | TimescaleDB Hypertable (`daily_price_history`) with 360-day chunk interval |
| **Price Records** | 287,310 Daily OHLCV Records (2000–2026) |
| **Corporate Actions** | 1,653 Dividends and Stock Splits |
| **Relational Database** | PostgreSQL (`stock_market_db` on port 5435) |
| **Time-Series Database** | TimescaleDB (`stock_timescale_db` on port 5434) |
| **ML Engine** | HistGradientBoosting Classifier (Horizon: 5 trading days, Class-weighted) |
| **Security & Auth** | Passwords hashed with `bcrypt` (12 rounds), JWT tokens via HttpOnly cookies and Bearer headers |
| **Latest Market Date** | **2026-01-30** |

---

## 🏗 Architecture

```
┌─────────────────────────────────┐
│       React + Vite Frontend     │  (Port 5173 - Dark Financial UI)
│   (AuthContext, Recharts, CSS)  │
└────────────────┬────────────────┘
                 │ HTTP / REST (JWT Cookies & Bearer Tokens)
┌────────────────▼────────────────┐
│         FastAPI Backend         │  (Port 8000 - Python 3.12)
│  (Auth, Trading, ML Inference)  │
└───────┬─────────────────┬───────┘
        │                 │
        │ Parameterized   │ Time-Bucket &
        │ SQL & Locks     │ Analytical Queries
        ▼                 ▼
┌──────────────────┐   ┌───────────────────────────┐
│ PostgreSQL 17    │   │ TimescaleDB (Docker)      │
│ (Port 5435)      │   │ (Port 5434)               │
│ stock_market_db  │   │ stock_timescale_db        │
├──────────────────┤   ├───────────────────────────┤
│ • app_user       │   │ • daily_price_history     │
│ • user_portfolio │   │   (Hypertable: 360d chunk)│
│ • holdings       │   │ • 287,310 time-series rows│
│ • transactions   │   └───────────────────────────┘
│ • audit_log      │
│ • user_watchlist │
└──────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (for TimescaleDB time-series container on port 5434)
- **PostgreSQL 17** (running on port 5435, database `stock_market_db`)
- **Python 3.10+** (virtual environment located in `./venv`)
- **Node.js 18+** and npm

---

### ⚡ Start Everything with a Single Command

To start the database container, FastAPI backend, and React/Vite frontend all together, simply run from the project root:

```bash
./start.sh
```

This single command will:
1. Verify ports `8000` (backend) and `5173` (frontend) are available and prevent conflicts.
2. Ensure the TimescaleDB Docker container (`dbs_timescaledb`) is started.
3. Launch the FastAPI backend using `./venv` on `http://127.0.0.1:8000`.
4. Poll the backend health check (`/api/health`) until verified healthy.
5. Launch the React/Vite frontend on `http://localhost:5173`.
6. Print the service URLs and monitor both processes simultaneously.

**Stopping the Application**:
- Press `Ctrl+C` in the terminal running `./start.sh` to cleanly stop both the frontend and backend servers.
- Or run the companion stop script:
  ```bash
  ./stop.sh        # Stops frontend and backend processes
  ./stop.sh --all  # Stops frontend, backend, and TimescaleDB Docker container
  ```

---

### Safe Environment Setup (.env)

Copy the safe template `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Ensure `.env` in the project root is configured with your database ports and passwords:

```ini
# PostgreSQL — Relational Database (stock_market_db)
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password_here
POSTGRES_DB=stock_market_db

# TimescaleDB — Time-Series Database (stock_timescale_db)
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5434
TIMESCALE_USER=postgres
TIMESCALE_PASSWORD=your_timescale_password_here
TIMESCALE_DB=stock_timescale_db

# JWT Authentication
JWT_SECRET=your_jwt_secret_key_here
```

---

### Database Initialization & Migrations

1. **Start TimescaleDB Container**:
   ```bash
   docker compose up -d
   ```

2. **Initialize PostgreSQL Relational Schema**:
   ```bash
   psql -h localhost -p 5435 -U postgres -d stock_market_db -f sql/schema/01_create_schema.sql
   ```

3. **Execute Historical Data Ingestion**:
   ```bash
   ./venv/bin/python scripts/ingest_data.py
   ```

4. **Database Normalization Migrations** (in `sql/migration/`):
   - `01_stage_replacement_360d.sql`: Optimized time-series chunking.
   - `02_atomic_cutover.sql`: Non-blocking cutover for hypertable.
   - `04_auth_and_user_portfolios.sql`: User authentication and paper-trading schema.
   - `05_pure_3nf_and_risk_normalization.sql`: Pure 3NF relational normalization & audit ledger.
   - `06_retire_risk_jsonb_column.sql`: Full cutover to normalized risk tables.

---

### Manual / Component-by-Component Startup (Alternative)

If you prefer to start components individually:

#### 1. Start Backend Server
```bash
./venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation (Swagger UI) is available at: **http://127.0.0.1:8000/docs**

#### 2. Start Frontend Dev Server
```bash
cd frontend
npm run dev
```
Open **http://127.0.0.1:5173** in your browser.

---

## 📐 Database Normalization & ER Architecture

A major highlight of this DBMS project is the academic rigorous normalization performed on raw, unnormalized NSE stock-market feeds.

- **Full Normalization Report**: [docs/database-design/normalization-report.md](docs/database-design/normalization-report.md)
- **Digital ER Diagram**: [docs/er-diagram/er-diagram-digital.md](docs/er-diagram/er-diagram-digital.md)

### Key DBMS Architectural Highlights:
1. **1NF Compliance**: Eliminated repeating multi-value attributes (corporate dividends, stock splits) into a separate `corporate_action` entity.
2. **2NF Compliance**: Eliminated partial dependencies on composite keys `(ticker, trading_date)` by isolating company descriptive attributes (`company_name`, `industry`, `listing_date`) from daily time-series records.
3. **3NF & BCNF Compliance**: Eliminated transitive dependencies $A \to B \to C$ (e.g., $\text{ticker} \to \text{sector\_name} \to \text{sector\_id}$) by creating an independent `sector` lookup entity with surrogate foreign keys.
4. **Lossless Join Decompositions**: Every vertical decomposition preserves functional dependencies and satisfies Heath's Theorem: $R_1 \cap R_2 \to R_1$ or $R_1 \cap R_2 \to R_2$.
5. **Storage Optimization**: Eliminated 7.18 MB of redundant text and float data across 287,310 records, reducing storage footprints by 12.44% while accelerating query execution.

---

## 🧪 Testing and Verification

Run the complete backend test suite:

```bash
# Run all 72 tests across API, Auth, Trading, Normalization, and ML
./venv/bin/pytest tests/ -v
```

### Test Coverage Highlights (72 Passed Tests):
- `tests/test_api.py`: 35 tests verifying health checks, dual database connections, TimescaleDB time-bucket aggregation, corporate actions, and company fundamentals.
- `tests/test_auth_and_portfolio.py`: 16 tests verifying user registration, duplicate email rejection, bcrypt security, JWT authentication, portfolio isolation, paper trading orders, overselling rejection, and dashboard KPI synchronization.
- `tests/test_ml_pipeline.py`: 12 tests verifying no lookahead data leakage, probability normalization, and chronological train/test embargo boundaries.
- `tests/test_normalized_portfolio_and_risk.py`: 8 tests validating 3NF relational normalization, weighted-average cost basis accounting, multi-portfolio management, and transaction ledger audit triggers.
- `tests/test_paper_trading.py`: Complete end-to-end integration test of the paper trading lifecycle.

### Frontend Production Build:
```bash
cd frontend && npm run build
```

---

## 🎓 DBMS Project Demonstration Guide

Follow these steps and representative SQL queries during your live project presentation:

### Step 1: User Registration
Register a new user in the web UI at `http://127.0.0.1:5173/register` or via API.
Verify in PostgreSQL:
```sql
SELECT user_id, email, full_name, created_at
FROM app_user
ORDER BY user_id DESC
LIMIT 1;
```

### Step 2: Automatic Portfolio Provisioning
Verify the default "Main Portfolio" and initial ₹100,000 cash balance:
```sql
SELECT portfolio_id, user_id, portfolio_name, cash_balance, created_at
FROM user_portfolio
WHERE user_id = (SELECT MAX(user_id) FROM app_user);
```

### Step 3: Stock Purchase (BUY Transaction)
In the UI, click **+ Buy Stock**, select `RELIANCE.NS`, quantity `10`, price `₹2500.00`.
Verify the transaction and cash balance reduction to ₹75,000.00:
```sql
-- Verify Portfolio Cash Deduction
SELECT portfolio_name, cash_balance
FROM user_portfolio
WHERE user_id = (SELECT MAX(user_id) FROM app_user);

-- Verify Upserted Holding
SELECT holding_id, ticker, quantity, average_buy_price, invested_value
FROM portfolio_holding
WHERE portfolio_id = (SELECT portfolio_id FROM user_portfolio WHERE user_id = (SELECT MAX(user_id) FROM app_user));

-- Verify Transaction Ledger Entry
SELECT transaction_id, ticker, transaction_type, quantity, price
FROM portfolio_transaction
WHERE user_id = (SELECT MAX(user_id) FROM app_user)
ORDER BY transaction_id DESC
LIMIT 1;

-- Verify Audit Trigger Execution
SELECT audit_id, operation, transaction_id, ticker, transaction_type, price, quantity, audit_timestamp
FROM portfolio_transaction_audit
ORDER BY audit_id DESC
LIMIT 1;
```

### Step 4: Stock Sale (SELL Transaction)
In the UI, click **- Sell** on `RELIANCE.NS`, sell `5` shares at `₹2600.00`.
Verify cash balance increased by ₹13,000 to ₹88,000, and remaining shares equal 5:
```sql
SELECT cash_balance FROM user_portfolio WHERE user_id = (SELECT MAX(user_id) FROM app_user);
SELECT ticker, quantity, invested_value FROM portfolio_holding WHERE user_id = (SELECT MAX(user_id) FROM app_user);
```

### Step 5: Personalized Watchlist CRUD
In the UI, go to **Watchlist**, add `TCS.NS` with alert price `₹3600.00`.
Verify insertion and uniqueness constraint:
```sql
SELECT watchlist_id, user_id, ticker, alert_price, added_at
FROM user_watchlist
WHERE user_id = (SELECT MAX(user_id) FROM app_user);
```

### Step 6: Multi-User Isolation
Log in as a second user (or run `tests/test_auth_and_portfolio.py`).
Verify User B cannot view User A's holdings or transactions:
```sql
-- Demonstrates foreign key constraints and user ownership isolation
SELECT p.portfolio_id, p.portfolio_name, u.email
FROM user_portfolio p
JOIN app_user u ON p.user_id = u.user_id
ORDER BY p.portfolio_id DESC
LIMIT 2;
```

---

## ⚖️ Known Limitations

1. **Market Data Boundary**: Historical stock records span up to **2026-01-30**. Market valuation calculations use the latest recorded market prices from this snapshot.
2. **Simulated Execution**: Stock orders execute against the system's internal paper trading cash account rather than a live brokerage exchange.
