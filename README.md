# DBS Stock Market Analytics and Portfolio Management System

## 1. Project Title

**DBS Stock Market Analytics and Portfolio Management System**

## 2. Problem Statement

Investors often find it difficult to analyse historical stock market data, track stock performance, manage their portfolios, and make informed investment decisions. Managing large volumes of historical financial records also creates significant challenges in database storage, query latency, and analytical throughput.

This project addresses these challenges by developing a centralized stock market analytics and portfolio management platform that leverages a dual-database architecture—combining relational PostgreSQL with time-series TimescaleDB—to efficiently store, process, and analyze financial market information.

## 3. Abstract

The DBS Stock Market Analytics and Portfolio Management System is designed to help users analyse stock market data and manage their investment portfolios. The system uses PostgreSQL for relational data management and TimescaleDB for handling time-series financial data. It contains historical stock price information for Nifty 50 companies from 1999 to 2026, along with corporate actions such as dividends and stock splits. The project includes database views, stored procedures, triggers, and analytical SQL queries to support efficient data processing and portfolio-related operations. The application also provides a user interface for interacting with the system and viewing relevant financial information.

## 4. Team Members

| S. No. | Name | Register Number |
|---|---|---|
| 1 | Easwar A P | 25BCE1512 |
| 2 | Mohamed Irfan | 25BCE1462 |
| 3 | Mohammed Nadeem | 25BCE1771 |

## 5. Functional Features

- **Historical Stock Data Management**: Long-term OHLCV price histories and corporate actions for 49 Nifty 50 blue-chip companies.
- **Time-Series Analysis**: High-performance hypertable time-bucket aggregations powered by TimescaleDB.
- **Portfolio & Paper Trading**: Virtual portfolio management with cash balance accounting, trade execution, and weighted average cost basis calculations.
- **Watchlist & Price Alerts**: User-configurable watchlists with price threshold alerts and trigger tracking.
- **Machine Learning Forecasts**: Trend prediction pipeline utilizing HistGradientBoosting classification over 5-day trading horizons.
- **Automated Database Consistency**: Database triggers enforcing ledger immutability, stock availability checks, and audit logging.
- **Stored Procedures & Views**: Encapsulated procedures for trade recording and analytical views for fundamentals, volatility, and sector performance.
- **Interactive Financial Dashboard**: Responsive web interface with dark financial UI, interactive charts, and valuation screens.

## 6. Technology Stack

| Component | Technology |
|---|---|
| Relational Database | PostgreSQL 17 / 18 (Port 5435) |
| Time-Series Database | TimescaleDB (PostgreSQL 17 Hypertable, Port 5434) |
| Database Containerization | Docker & Docker Compose |
| Backend Framework | FastAPI (Python 3.12, Uvicorn, SQLAlchemy) |
| Frontend Framework | React 18, Vite, Recharts, Lucide Icons |
| Machine Learning | Scikit-learn (HistGradientBoosting), Pandas, NumPy |
| Authentication & Security | JWT Tokens, Bcrypt Password Hashing |
| Version Control | Git & GitHub |

## 7. Database Software and Requirements

### Software Requirements

- **PostgreSQL 17 or 18** (Relational instance on port 5435)
- **Docker Desktop** (To run the TimescaleDB container on port 5434)
- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 18+ and npm** (For frontend dependencies)
- **Git**

### Hardware Requirements

- Minimum 8 GB RAM (16 GB recommended for running dual databases and frontend simultaneously).
- Minimum 2 GB free disk space for historical datasets, database indexes, and node modules.

## 8. Database Architecture

The system utilizes a dual-database architecture to separate relational operations from high-volume time-series processing:

1. **PostgreSQL (`stock_market_db` on port 5435)**:
   - Manages relational domain entities including users, portfolios, cash balances, transactions, company profiles, fundamentals, corporate actions, and audit logs.
   - Enforces referential integrity (foreign keys), ACID compliance, and concurrency locking (`SELECT FOR UPDATE`).

2. **TimescaleDB (`stock_timescale_db` on port 5434 in Docker)**:
   - Stores 287,310+ historical daily price records in the `daily_price_history` hypertable partitioned by 360-day chunks.
   - Provides optimized time-series rollups, moving averages, and OHLC candlestick aggregations.

## 9. Database Tables, Relationships, and Sample Data

The relational schema consists of 13 interconnected tables adhering to Boyce-Codd Normal Form (BCNF) and Third Normal Form (3NF):

- **Market Classification & Securities**:
  - `sector`: Industrial classifications (13 sectors).
  - `company`: Company directory (49 Nifty 50 companies; FK to `sector`).
  - `daily_price_history`: Historical OHLCV market quotes (composite PK: `ticker, trading_date`; FK to `company`).
  - `corporate_action`: Dividend distributions and stock split events (FK to `company`).
  - `current_fundamentals`: P/E, EPS, Beta, Market Cap, and valuation multiples (FK to `company`).
  - `stock_summary`: Long-term trading statistics and historical returns (FK to `company`).

- **User & Portfolio Management**:
  - `app_user`: User credentials with bcrypt password hashes and roles.
  - `user_portfolio`: User investment accounts with cash balance tracking (FK to `app_user`).
  - `portfolio_holding`: Aggregated stock holdings adhering to 3NF (FK to `user_portfolio`, FK to `company`).
  - `portfolio_transaction`: Immutable audit ledger of all BUY/SELL orders (FK to `user_portfolio`, FK to `company`).
  - `user_watchlist`: Target price alert watchlists (FK to `app_user`, FK to `company`).
  - `alert`: System notifications and price alerts (FK to `app_user`, FK to `company`).

- **Risk & Predictions**:
  - `portfolio_risk_analysis` & `portfolio_risk_sector_allocation`: Sharpe ratio, volatility, and sector allocations.
  - `ml_prediction`: Model inference forecast outputs (FK to `company`).

### Sample Dataset

- **49 Listed Companies**: Complete Nifty 50 universe (e.g., RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS).
- **287,310 Daily Price Records**: Continuous daily trading sessions spanning 1999–2026.
- **1,653 Corporate Action Events**: Historical dividends and stock split adjustments.

## 10. Application Setup and Execution

### Step 1: Clone the Repository

```bash
git clone https://github.com/easwararun5-dotcom/DBS-Stock-Market-Analytics.git
cd DBS-Stock-Market-Analytics
```

### Step 2: Configure Environment Variables

Create your local `.env` configuration file from the template:

```bash
cp .env.example .env
```

Adjust the database credentials in `.env` if your local PostgreSQL settings differ from the defaults.

### Step 3: Start TimescaleDB Service

Start the TimescaleDB Docker container:

```bash
docker compose up -d
```

Verify the container is healthy using `docker ps`.

### Step 4: Initialize the Database Schema

Create tables, indexes, views, and functions in your relational database:

```bash
psql -h localhost -p 5435 -U <username> -d stock_market_db -f database/schema.sql
```

*(Note: Stored procedures and triggers can also be initialized from `database/procedures/` and `database/triggers/` if rebuilding from scratch).*

### Step 5: Load Sample Data

Seed the database with sample companies, fundamentals, and demo accounts:

```bash
psql -h localhost -p 5435 -U <username> -d stock_market_db -f database/sample_data.sql
```

To ingest the full 287,000+ historical records:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/scripts/ingest_data.py
```

### Step 6: Run the Application

#### Option A: Unified Startup Script (Recommended)

Run the provided startup script to start both backend and frontend servers:

```bash
./start.sh
```

To stop all running services cleanly:

```bash
./stop.sh
```

#### Option B: Manual Startup

**Start Backend (FastAPI):**
```bash
source venv/bin/activate
export PYTHONPATH=src
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Start Frontend (React / Vite):**
```bash
cd src/frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173`. Backend interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

## 11. Implemented Database Components

- **13 Relational Tables**: Full schema with referential integrity constraints and primary keys.
- **6 Analytical Views**: Pre-aggregated metrics (`v_latest_stock_prices`, `v_company_fundamentals`, `v_stock_performance`, `v_sector_performance`, `v_stock_volatility`, `v_corporate_action_summary`).
- **7 Stored Procedures**: Transaction management and portfolio valuation routines (`database/procedures/`).
- **2 Database Triggers**: Audit logging and balance consistency checks (`database/triggers/`).
- **10 Analytical SQL Files**: Categorized SQL query suite (`database/queries/`).

## 12. Screenshots and Summary of Implemented Features

High-resolution application and database evidence screenshots are available in the [`screenshots/`](screenshots/) directory:

- `screenshots/WhatsApp Image 2026-11-03 at 21.07.16.jpeg`: Stock Explorer with interactive historical price chart, valuation multiples, and company fundamentals.
- `screenshots/WhatsApp Image 2026-11-03 at 21.07.17.jpeg`: User Portfolio Dashboard showing live asset allocation, cash balance, and trade execution interface.
- `screenshots/WhatsApp Image 2026-11-03 at 21.07.17 (1).jpeg`: Machine Learning Trend Prediction screen displaying class probabilities, direction forecasts, and model confidence scores.
- `screenshots/WhatsApp Image 2026-11-03 at 21.07.18.jpeg`: Watchlist and Price Alerts interface with target price tracking.

## 13. Testing Instructions

Automated test suites validate query syntax, database triggers, concurrency locks, and API endpoints.

### Run Full Test Suite

```bash
source venv/bin/activate
pytest tests/
```

### Run Database & Analytical SQL Tests

```bash
python src/scripts/test_queries.py
python src/scripts/test_triggers.py
```

### Verification Checklist

- Successful dual-database connectivity (PostgreSQL port 5435 & TimescaleDB port 5434).
- Correct execution of all 10 analytical SQL queries.
- Trigger rejection of invalid stock transactions (e.g., selling more shares than owned).
- Correct calculations for portfolio valuations, profit/loss, and moving averages.

## 14. Known Limitations

1. **Historical Market Data Boundary**: The dataset spans trading sessions up to January 30, 2026. The application does not connect to live streaming exchange feeds for intraday tick updates.
2. **Simulated Order Execution**: Orders are executed against the internal virtual paper-trading cash account rather than an external brokerage exchange.
3. **TimescaleDB Container Prerequisite**: Advanced time-bucket queries require the Docker TimescaleDB container to be running. If Docker is offline, the API falls back to standard PostgreSQL relational tables.
4. **Academic Project Scope**: The platform and ML trend predictions are developed strictly for academic demonstration and DBMS assignment evaluation, not for financial investment advice.

## 15. YouTube Demonstration

**Project Demonstration Video:** https://youtu.be/xEibkMBX38E

The video demonstration covers application interface features, dual-database architecture, PostgreSQL & TimescaleDB queries, data ingestion, stored procedures, triggers, and live test executions.

## 16. Repository

GitHub Repository: https://github.com/easwararun5-dotcom/DBS-Stock-Market-Analytics
