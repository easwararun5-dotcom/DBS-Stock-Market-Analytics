# DBS Stock Market Analytics & Portfolio Management System

A full-stack financial analytics application built as a Database Systems (DBS) college project. Features real-time stock data visualization, sector analysis, portfolio tracking, and an ML prediction framework using **FastAPI**, **React**, **TimescaleDB**, and **PostgreSQL**.

## 📊 Dataset

| Metric | Value |
|--------|-------|
| Companies | 49 (Nifty 50 universe) |
| Sectors | 13 |
| Daily Price Records | 287,310 |
| Corporate Actions | 1,653 |
| Fundamentals | 49 |
| Latest Data Date | **2026-01-30** |

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────────┐
│   React +   │────▶│   FastAPI     │────▶│   TimescaleDB      │
│   Vite      │     │   Backend     │     │   (PostgreSQL 17)  │
│   :5173     │     │   :8000       │     │   :5433 (host)     │
└─────────────┘     └──────────────┘     └────────────────────┘
   Frontend           16 API              Docker container
                      endpoints           dbs_timescaledb
```

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (running, with `dbs_timescaledb` container up)
- **Python 3.10+** (`py` launcher on Windows)
- **Node.js 18+** and npm

### 1. Start the Database

```bash
docker compose up -d
```

The TimescaleDB container must be running with the `stock_timescale_db` database already populated. Do **not** rerun schema creation or data ingestion.

### 2. Configure Environment

```bash
# From project root
copy .env.example .env
# Edit .env with your database password (default: postgres)
```

### 3. Install Backend Dependencies

```bash
py -m pip install -r backend/requirements.txt
```

### 4. Start the Backend Server

```bash
py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The API is now available at **http://localhost:8000**. API docs at **http://localhost:8000/docs**.

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 6. Start the Frontend Dev Server

```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

### 7. Run Tests

```bash
# From project root
py -m pytest tests/test_api.py -v
```

## 📡 API Endpoints

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | GET | `/api/health` | Health check & database connectivity |
| 2 | GET | `/api/dashboard` | Dashboard aggregate statistics |
| 3 | GET | `/api/prices/latest` | Latest prices for all 49 companies |
| 4 | GET | `/api/prices/{ticker}` | Historical OHLCV data (with date range, limit, order) |
| 5 | GET | `/api/companies` | List/search companies (with search, sector filter, pagination) |
| 6 | GET | `/api/companies/{ticker}` | Detailed company info (fundamentals + summary + latest price) |
| 7 | GET | `/api/sectors` | Sector performance overview (13 sectors) |
| 8 | GET | `/api/summary` | Stock summary statistics (sortable) |
| 9 | GET | `/api/volatility` | 20-day volatility and MA crossover signals |
| 10 | GET | `/api/corporate-actions` | Corporate actions with ticker/type filters, pagination |
| 11 | GET | `/api/corporate-actions/summary` | Per-company corporate action summary |
| 12 | GET | `/api/performance` | Stock performance metrics |
| 13 | GET | `/api/analytics/time-bucket/{ticker}` | TimescaleDB time-bucket aggregations |
| 14 | GET | `/api/ml/status` | ML model training status |
| 15 | GET | `/api/ml/predictions` | ML predictions (if any exist) |
| 16 | GET | `/api/watchlist?user_id=N` | User watchlist (demo mode) |
| 17 | GET | `/api/portfolio/holdings?user_id=N` | Portfolio holdings (demo mode) |
| 18 | GET | `/api/portfolio/transactions?user_id=N` | Transaction history (demo mode) |

All endpoints use **parameterised SQL queries** against real database tables and views.

## 🖥 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Market overview with stats, top gainers/losers, sector chart |
| Stock Explorer | `/stocks` | Search & browse all 49 stocks with sorting/filtering |
| Stock Detail | `/stocks/:ticker` | Price chart (1M–All range), fundamentals, summary |
| Sectors | `/sectors` | Sector-level P/E, returns, market cap analysis |
| Portfolio | `/portfolio` | Holdings, allocation pie chart, transactions (demo mode) |
| Watchlist | `/watchlist` | Tracked stocks with alerts (demo mode) |
| ML Predictions | `/ml` | ML status — honestly reports "Not Trained Yet" |

## 🗃 Database Schema

13 tables across 3 domains:

**Market Data**: `company`, `sector`, `daily_price_history`, `current_fundamentals`, `stock_summary`, `corporate_action`

**User/Portfolio**: `app_user`, `portfolio_holding`, `portfolio_transaction`, `user_watchlist`, `alert`, `portfolio_risk_analysis`

**ML**: `ml_prediction`

6 views: `v_latest_stock_prices`, `v_company_fundamentals`, `v_sector_performance`, `v_stock_performance`, `v_stock_volatility`, `v_corporate_action_summary`

## ⚠️ Known Limitations

- **No authentication**: Portfolio and watchlist features operate in demo mode with a hardcoded user ID. Data is not user-specific or secure.
- **ML not trained**: The ML prediction section honestly displays "Not Trained Yet". No fake predictions are shown. The `ml_prediction` table schema is preserved for future use.
- **Read-only API**: No write endpoints for portfolio transactions or watchlist management are implemented (would require authentication first).
- **Static dataset**: Data is current through 2026-01-30. No live market data feed.
- **`daily_price_history` is not a hypertable**: TimescaleDB's `time_bucket()` function works but without hypertable optimizations.

## 📁 Project Structure

```
DBS-Stock-Market-Analytics/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── database.py          # Database configuration (env vars)
│   │   └── main.py              # FastAPI endpoints (16 routes)
│   ├── requirements.txt
│   └── scripts/                 # Migration & test scripts (preserved)
├── frontend/
│   ├── src/
│   │   ├── api.js               # API client
│   │   ├── main.jsx             # Entry point
│   │   ├── App.jsx              # Router
│   │   ├── index.css            # Global styles
│   │   ├── components/
│   │   │   ├── Layout.jsx       # Sidebar navigation
│   │   │   └── Common.jsx       # Shared UI components
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── StockExplorer.jsx
│   │       ├── StockDetail.jsx
│   │       ├── Sectors.jsx
│   │       ├── Portfolio.jsx
│   │       ├── Watchlist.jsx
│   │       └── MLPredictions.jsx
│   ├── .env                     # Frontend env config
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── sql/                         # SQL scripts (preserved)
├── scripts/                     # Ingestion scripts (preserved)
├── data/                        # Raw datasets (preserved)
├── docs/                        # Documentation (preserved)
├── tests/
│   ├── test_api.py              # 28 API integration tests
│   ├── test_portfolio_lifecycle.sql
│   └── test_triggers.sql
├── .env                         # Backend env config (git-ignored)
├── .env.example                 # Template without credentials
├── docker-compose.yml
└── README.md
```

## ✅ Test Results

```
28 passed in ~5s

tests/test_api.py::TestHealth (2 tests)
tests/test_api.py::TestDashboard (3 tests)
tests/test_api.py::TestLatestPrices (2 tests)
tests/test_api.py::TestPriceHistory (3 tests)
tests/test_api.py::TestCompanies (5 tests)
tests/test_api.py::TestSectors (1 test)
tests/test_api.py::TestStockSummary (2 tests)
tests/test_api.py::TestVolatility (1 test)
tests/test_api.py::TestCorporateActions (3 tests)
tests/test_api.py::TestPerformance (1 test)
tests/test_api.py::TestML (2 tests)
tests/test_api.py::TestWatchlistPortfolio (3 tests)
```
