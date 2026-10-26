"""
DBS Stock Market Analytics & Portfolio Management System — FastAPI Backend

Read-only API endpoints serving real data from the stock_timescale_db database.
All queries use parameterised SQL against actual verified table/view definitions.

Tables used:
  company, sector, daily_price_history, current_fundamentals, stock_summary,
  corporate_action, user_watchlist, portfolio_holding, portfolio_transaction,
  ml_prediction, app_user

Views used:
  v_latest_stock_prices, v_company_fundamentals, v_sector_performance,
  v_stock_performance, v_stock_volatility, v_corporate_action_summary
"""

import time
from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, Query, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from .database import get_db, DB_HOST, DB_PORT, DB_NAME
except ImportError:
    from database import get_db, DB_HOST, DB_PORT, DB_NAME


# ===========================================================================
# App Setup
# ===========================================================================
app = FastAPI(
    title="DBS Stock Market Analytics API",
    description=(
        "Backend API for the DBS Stock Market Analytics & Portfolio Management System. "
        "Provides access to 49 Nifty-50 companies, 287K+ daily price records, "
        "fundamentals, sector analysis, corporate actions, and portfolio management."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Pydantic Response Models
# ===========================================================================
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: Dict[str, Any]


class DashboardStats(BaseModel):
    total_companies: int
    total_sectors: int
    total_price_records: int
    total_corporate_actions: int
    latest_data_date: Optional[str] = None
    market_cap_total_trillion: Optional[float] = None
    top_gainers: List[Dict[str, Any]] = []
    top_losers: List[Dict[str, Any]] = []
    sector_breakdown: List[Dict[str, Any]] = []


class CompanyItem(BaseModel):
    ticker: str
    company_name: str
    sector_name: str


class CompanyDetail(BaseModel):
    ticker: str
    company_name: str
    sector_name: str
    fundamentals: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    latest_price: Optional[Dict[str, Any]] = None


class PriceRecord(BaseModel):
    ticker: str
    trading_date: str
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[int] = None
    daily_return: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None


class PaginatedResponse(BaseModel):
    data: List[Any]
    total: int
    page: int
    per_page: int
    total_pages: int


# ===========================================================================
# Helper
# ===========================================================================
def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row/RowMapping to a plain dict with serialisable values."""
    if hasattr(row, "_mapping"):
        d = dict(row._mapping)
    elif hasattr(row, "_asdict"):
        d = row._asdict()
    else:
        d = dict(row)
    # Convert date/datetime to ISO strings, Decimal to float
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            d[k] = v.isoformat()
        elif hasattr(v, "is_finite"):  # Decimal
            d[k] = float(v) if v.is_finite() else None
    return d


# ===========================================================================
# 1. Health Check
# ===========================================================================
@app.get("/api/health", summary="Health & database connectivity check")
def health_check(db: Session = Depends(get_db)):
    result: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": {
            "host": DB_HOST,
            "port": int(DB_PORT),
            "name": DB_NAME,
            "connected": False,
        },
    }
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000

        # Check hypertable status for daily_price_history
        ht = db.execute(
            text(
                "SELECT table_name FROM _timescaledb_catalog.hypertable "
                "WHERE table_name = 'daily_price_history'"
            )
        ).fetchone()

        result["database"]["connected"] = True
        result["database"]["latency_ms"] = round(latency, 2)
        result["database"]["hypertable"] = ht[0] if ht else None
    except Exception as e:
        result["status"] = "unhealthy"
        result["database"]["error"] = str(e)
    return result


# ===========================================================================
# 2. Dashboard Statistics
# ===========================================================================
@app.get("/api/dashboard", summary="Dashboard aggregate statistics")
def dashboard_stats(db: Session = Depends(get_db)):
    try:
        counts = db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM company) AS companies,
                (SELECT COUNT(*) FROM sector) AS sectors,
                (SELECT COUNT(*) FROM daily_price_history) AS prices,
                (SELECT COUNT(*) FROM corporate_action) AS corp_actions,
                (SELECT MAX(trading_date) FROM daily_price_history) AS latest_date,
                (SELECT ROUND(SUM(market_cap) / 1e12, 2) FROM current_fundamentals) AS total_mcap_t
        """)).fetchone()

        top_gainers = db.execute(text("""
            SELECT ticker, company_name, sector_name,
                   close_price, daily_return_pct
            FROM v_latest_stock_prices
            WHERE daily_return_pct IS NOT NULL
            ORDER BY daily_return_pct DESC
            LIMIT 5
        """)).fetchall()

        top_losers = db.execute(text("""
            SELECT ticker, company_name, sector_name,
                   close_price, daily_return_pct
            FROM v_latest_stock_prices
            WHERE daily_return_pct IS NOT NULL
            ORDER BY daily_return_pct ASC
            LIMIT 5
        """)).fetchall()

        sectors = db.execute(text("""
            SELECT sector_name, num_companies,
                   total_market_cap_trillion_inr,
                   avg_pe_ratio
            FROM v_sector_performance
            ORDER BY total_market_cap_trillion_inr DESC NULLS LAST
        """)).fetchall()

        return {
            "total_companies": counts[0],
            "total_sectors": counts[1],
            "total_price_records": counts[2],
            "total_corporate_actions": counts[3],
            "latest_data_date": counts[4].isoformat() if counts[4] else None,
            "market_cap_total_trillion": float(counts[5]) if counts[5] else None,
            "top_gainers": [_row_to_dict(r) for r in top_gainers],
            "top_losers": [_row_to_dict(r) for r in top_losers],
            "sector_breakdown": [_row_to_dict(r) for r in sectors],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard query failed: {e}")


# ===========================================================================
# 3. Latest Prices (all companies)
# ===========================================================================
@app.get("/api/prices/latest", summary="Latest available prices for all companies")
def latest_prices(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("""
            SELECT ticker, company_name, sector_name,
                   latest_trading_date, open_price, high_price,
                   low_price, close_price, volume,
                   daily_return_pct, volatility_20d_pct,
                   ma_50, ma_200, intraday_range
            FROM v_latest_stock_prices
            ORDER BY ticker
        """)).fetchall()
        return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 4. Historical Prices for a Ticker
# ===========================================================================
@app.get("/api/prices/{ticker}", summary="Historical OHLCV data for a ticker")
def price_history(
    ticker: str = PathParam(..., description="Stock ticker symbol"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(5000, ge=1, le=50000),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    clean = ticker.strip().upper()

    # Verify ticker exists
    exists = db.execute(
        text("SELECT 1 FROM company WHERE ticker = :t"), {"t": clean}
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Ticker '{clean}' not found")

    filters = ["ticker = :ticker"]
    params: Dict[str, Any] = {"ticker": clean, "limit": limit}

    if start_date:
        filters.append("trading_date >= CAST(:start_date AS date)")
        params["start_date"] = start_date
    if end_date:
        filters.append("trading_date <= CAST(:end_date AS date)")
        params["end_date"] = end_date

    where = " AND ".join(filters)
    direction = "ASC" if order == "asc" else "DESC"

    sql = f"""
        SELECT ticker, trading_date, open_price, high_price, low_price,
               close_price, volume, daily_return, ma_50, ma_200
        FROM daily_price_history
        WHERE {where}
        ORDER BY trading_date {direction}
        LIMIT :limit
    """
    try:
        rows = db.execute(text(sql), params).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    data = [_row_to_dict(r) for r in rows]

    # Also get total count for this ticker
    count_params = {k: v for k, v in params.items() if k != "limit"}
    count_sql = f"SELECT COUNT(*) FROM daily_price_history WHERE {where}"
    total = db.execute(text(count_sql), count_params).scalar()

    return {"ticker": clean, "total_records": total, "returned": len(data), "data": data}


# ===========================================================================
# 5. Company Search / Listing
# ===========================================================================
@app.get("/api/companies", summary="List or search companies")
def list_companies(
    search: Optional[str] = Query(None, description="Search by ticker or company name"),
    sector: Optional[str] = Query(None, description="Filter by sector name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    filters = []
    params: Dict[str, Any] = {}

    if search:
        filters.append(
            "(c.ticker ILIKE :search OR c.company_name ILIKE :search)"
        )
        params["search"] = f"%{search}%"
    if sector:
        filters.append("s.sector_name ILIKE :sector")
        params["sector"] = f"%{sector}%"

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    count_sql = f"""
        SELECT COUNT(*)
        FROM company c
        JOIN sector s ON c.sector_id = s.sector_id
        {where}
    """
    total = db.execute(text(count_sql), params).scalar()

    data_sql = f"""
        SELECT c.ticker, c.company_name, s.sector_name
        FROM company c
        JOIN sector s ON c.sector_id = s.sector_id
        {where}
        ORDER BY c.ticker
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(data_sql), params).fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
    }


# ===========================================================================
# 6. Company Detail (fundamentals + summary + latest price)
# ===========================================================================
@app.get("/api/companies/{ticker}", summary="Detailed company information")
def company_detail(ticker: str, db: Session = Depends(get_db)):
    clean = ticker.strip().upper()

    company = db.execute(
        text("""
            SELECT c.ticker, c.company_name, s.sector_name
            FROM company c
            JOIN sector s ON c.sector_id = s.sector_id
            WHERE c.ticker = :t
        """),
        {"t": clean},
    ).fetchone()

    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker '{clean}' not found")

    fundamentals = db.execute(
        text("SELECT * FROM v_company_fundamentals WHERE ticker = :t"),
        {"t": clean},
    ).fetchone()

    summary = db.execute(
        text("SELECT * FROM stock_summary WHERE ticker = :t"),
        {"t": clean},
    ).fetchone()

    latest = db.execute(
        text("SELECT * FROM v_latest_stock_prices WHERE ticker = :t"),
        {"t": clean},
    ).fetchone()

    return {
        "ticker": company[0],
        "company_name": company[1],
        "sector_name": company[2],
        "fundamentals": _row_to_dict(fundamentals) if fundamentals else None,
        "summary": _row_to_dict(summary) if summary else None,
        "latest_price": _row_to_dict(latest) if latest else None,
    }


# ===========================================================================
# 7. Sector Performance
# ===========================================================================
@app.get("/api/sectors", summary="Sector performance overview")
def sector_performance(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("""
            SELECT * FROM v_sector_performance
        """)).fetchall()
        return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# 8. Stock Summary / Statistics
# ===========================================================================
@app.get("/api/summary", summary="Stock summary statistics for all companies")
def stock_summary(
    sort_by: str = Query("ticker", description="Sort column"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    allowed_sorts = {
        "ticker", "total_return_pct", "volatility_pct", "avg_daily_volume",
        "highest_price", "lowest_price", "total_trading_days",
        "current_market_cap", "current_pe_ratio",
    }
    col = sort_by if sort_by in allowed_sorts else "ticker"
    direction = "ASC" if order == "asc" else "DESC"

    rows = db.execute(text(f"""
        SELECT ss.*, c.company_name, s.sector_name
        FROM stock_summary ss
        JOIN company c ON ss.ticker = c.ticker
        JOIN sector s ON c.sector_id = s.sector_id
        ORDER BY {col} {direction} NULLS LAST
    """)).fetchall()
    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}


# ===========================================================================
# 9. Stock Volatility
# ===========================================================================
@app.get("/api/volatility", summary="Stock volatility and MA crossover signals")
def stock_volatility(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT * FROM v_stock_volatility ORDER BY ticker")).fetchall()
    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}


# ===========================================================================
# 10. Corporate Actions
# ===========================================================================
@app.get("/api/corporate-actions", summary="Corporate actions (dividends & splits)")
def corporate_actions(
    ticker: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None, pattern="^(Dividend|Stock_Split)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    filters = []
    params: Dict[str, Any] = {}

    if ticker:
        filters.append("ca.ticker = :ticker")
        params["ticker"] = ticker.strip().upper()
    if action_type:
        filters.append("ca.action_type = :action_type")
        params["action_type"] = action_type

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    total = db.execute(
        text(f"SELECT COUNT(*) FROM corporate_action ca {where}"), params
    ).scalar()

    rows = db.execute(text(f"""
        SELECT ca.action_id, ca.ticker, c.company_name,
               ca.action_date, ca.action_type, ca.action_value
        FROM corporate_action ca
        JOIN company c ON ca.ticker = c.ticker
        {where}
        ORDER BY ca.action_date DESC
        LIMIT :limit OFFSET :offset
    """), params).fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
    }


# ===========================================================================
# 11. Corporate Action Summary (view)
# ===========================================================================
@app.get("/api/corporate-actions/summary", summary="Per-company corporate action summary")
def corporate_action_summary(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT * FROM v_corporate_action_summary ORDER BY ticker"
    )).fetchall()
    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}


# ===========================================================================
# 12. Stock Performance
# ===========================================================================
@app.get("/api/performance", summary="Stock performance metrics")
def stock_performance(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT * FROM v_stock_performance ORDER BY ticker"
    )).fetchall()
    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}


# ===========================================================================
# 13. Time-bucket analytics (TimescaleDB)
# ===========================================================================
@app.get("/api/analytics/time-bucket/{ticker}", summary="Time-bucket aggregations")
def time_bucket_analytics(
    ticker: str,
    interval: str = Query("7 days", description="Bucket interval"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    clean = ticker.strip().upper()
    allowed = {"1 day", "7 days", "14 days", "30 days"}
    safe_interval = interval if interval in allowed else "7 days"

    filters = ["ticker = :ticker"]
    params: Dict[str, Any] = {"ticker": clean}

    if start_date:
        filters.append("trading_date >= CAST(:start_date AS date)")
        params["start_date"] = start_date
    if end_date:
        filters.append("trading_date <= CAST(:end_date AS date)")
        params["end_date"] = end_date

    where = " AND ".join(filters)

    # time_bucket is a TimescaleDB function; if daily_price_history isn't a
    # hypertable it still works as a regular function.
    sql = f"""
        SELECT time_bucket('{safe_interval}', trading_date) AS bucket,
               ROUND(AVG(close_price), 4) AS avg_close,
               SUM(volume) AS total_volume,
               ROUND(MIN(low_price), 4) AS min_price,
               ROUND(MAX(high_price), 4) AS max_price,
               COUNT(*) AS record_count
        FROM daily_price_history
        WHERE {where}
        GROUP BY bucket
        ORDER BY bucket ASC
    """
    try:
        rows = db.execute(text(sql), params).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "ticker": clean,
        "interval": safe_interval,
        "total_buckets": len(rows),
        "data": [_row_to_dict(r) for r in rows],
    }


# ===========================================================================
# 14. ML Predictions — Status (deferred)
# ===========================================================================
@app.get("/api/ml/status", summary="ML prediction status")
def ml_status(db: Session = Depends(get_db)):
    """
    Returns the current state of ML predictions.
    ML training has NOT been performed yet — this endpoint honestly reports that.
    """
    count = db.execute(text("SELECT COUNT(*) FROM ml_prediction")).scalar()
    return {
        "ml_available": count > 0,
        "total_predictions": count,
        "status": "trained" if count > 0 else "not_trained",
        "message": (
            "ML model has not been trained yet. Predictions will be available "
            "after the ML pipeline is implemented, trained, and evaluated."
            if count == 0
            else f"{count} predictions available."
        ),
    }


@app.get("/api/ml/predictions", summary="ML predictions (if available)")
def ml_predictions(
    ticker: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns ML predictions if any exist. Does not fabricate data."""
    filters = []
    params: Dict[str, Any] = {}
    if ticker:
        filters.append("ticker = :ticker")
        params["ticker"] = ticker.strip().upper()

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    rows = db.execute(
        text(f"SELECT * FROM ml_prediction {where} ORDER BY prediction_date DESC"),
        params,
    ).fetchall()

    if not rows:
        return {
            "data": [],
            "total": 0,
            "message": (
                "No ML predictions available. The model has not been trained yet."
            ),
        }
    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows)}


# ===========================================================================
# 15. Watchlist (demo mode — no authentication)
# ===========================================================================
@app.get("/api/watchlist", summary="Watchlist items (demo mode)")
def get_watchlist(
    user_id: int = Query(..., description="User ID (demo mode — no auth)"),
    db: Session = Depends(get_db),
):
    """
    Returns watchlist items for a given user_id.
    NOTE: This is DEMO MODE — there is no authentication. The user_id is
    passed as a query parameter. In production, this would use authenticated
    sessions.
    """
    rows = db.execute(text("""
        SELECT w.watchlist_id, w.ticker, c.company_name,
               s.sector_name, w.alert_price, w.added_at,
               lp.close_price AS latest_price,
               lp.daily_return_pct,
               lp.latest_trading_date
        FROM user_watchlist w
        JOIN company c ON w.ticker = c.ticker
        JOIN sector sec ON c.sector_id = sec.sector_id
        LEFT JOIN v_latest_stock_prices lp ON w.ticker = lp.ticker
        JOIN sector s ON c.sector_id = s.sector_id
        WHERE w.user_id = :uid
        ORDER BY w.added_at DESC
    """), {"uid": user_id}).fetchall()

    return {"data": [_row_to_dict(r) for r in rows], "total": len(rows), "demo_mode": True}


# ===========================================================================
# 16. Portfolio Holdings (demo mode — no authentication)
# ===========================================================================
@app.get("/api/portfolio/holdings", summary="Portfolio holdings (demo mode)")
def get_holdings(
    user_id: int = Query(..., description="User ID (demo mode — no auth)"),
    db: Session = Depends(get_db),
):
    """
    Returns portfolio holdings for a given user_id.
    DEMO MODE — no authentication implemented.
    """
    rows = db.execute(text("""
        SELECT h.holding_id, h.ticker, c.company_name, s.sector_name,
               h.quantity, h.invested_value, h.average_buy_price,
               h.purchase_date,
               lp.close_price AS current_price,
               lp.latest_trading_date
        FROM portfolio_holding h
        JOIN company c ON h.ticker = c.ticker
        JOIN sector s ON c.sector_id = s.sector_id
        LEFT JOIN v_latest_stock_prices lp ON h.ticker = lp.ticker
        WHERE h.user_id = :uid
        ORDER BY h.ticker
    """), {"uid": user_id}).fetchall()

    holdings = [_row_to_dict(r) for r in rows]

    # Calculate P&L for each holding
    for h in holdings:
        if h.get("current_price") and h.get("invested_value"):
            current_val = float(h["quantity"]) * float(h["current_price"])
            invested = float(h["invested_value"])
            h["current_value"] = round(current_val, 2)
            h["profit_loss"] = round(current_val - invested, 2)
            h["profit_loss_pct"] = round(
                ((current_val - invested) / invested) * 100, 2
            ) if invested > 0 else 0

    return {"data": holdings, "total": len(holdings), "demo_mode": True}


@app.get("/api/portfolio/transactions", summary="Portfolio transactions (demo mode)")
def get_transactions(
    user_id: int = Query(..., description="User ID (demo mode — no auth)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Portfolio transaction history. DEMO MODE."""
    offset = (page - 1) * per_page

    total = db.execute(
        text("SELECT COUNT(*) FROM portfolio_transaction WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar()

    rows = db.execute(text("""
        SELECT t.transaction_id, t.ticker, c.company_name,
               t.transaction_type, t.transaction_date, t.price, t.quantity,
               t.holding_id
        FROM portfolio_transaction t
        JOIN company c ON t.ticker = c.ticker
        WHERE t.user_id = :uid
        ORDER BY t.transaction_date DESC
        LIMIT :limit OFFSET :offset
    """), {"uid": user_id, "limit": per_page, "offset": offset}).fetchall()

    return {
        "data": [_row_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
        "demo_mode": True,
    }
