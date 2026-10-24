import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Annotated
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from .database import (
        get_local_db,
        get_timescale_db,
        LOCAL_HOST,
        LOCAL_PORT,
        LOCAL_DB,
        TIMESCALE_HOST,
        TIMESCALE_PORT,
        TIMESCALE_DB,
    )
except ImportError:
    from database import (
        get_local_db,
        get_timescale_db,
        LOCAL_HOST,
        LOCAL_PORT,
        LOCAL_DB,
        TIMESCALE_HOST,
        TIMESCALE_PORT,
        TIMESCALE_DB,
    )

app = FastAPI(
    title="Stock Market Analytics & TimescaleDB API",
    description="FastAPI backend integrating PostgreSQL (port 5432) and TimescaleDB (port 5433).",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Response Schemas
# ---------------------------------------------------------------------------
class PriceRecord(BaseModel):
    ticker: str
    price_date: str
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[int] = None


class PriceHistoryResponse(BaseModel):
    ticker: str
    total_records: int
    data: List[PriceRecord]


class TimeBucketRecord(BaseModel):
    bucket: str
    avg_close_price: Optional[float] = None
    total_volume: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    record_count: int


class TimeBucketResponse(BaseModel):
    ticker: str
    interval: str
    total_buckets: int
    data: List[TimeBucketRecord]


# ---------------------------------------------------------------------------
# 1. GET /api/health
# ---------------------------------------------------------------------------
@app.get("/api/health", summary="Health check for local PostgreSQL and TimescaleDB")
def check_health(
    local_db: Session = Depends(get_local_db),
    timescale_db: Session = Depends(get_timescale_db)
) -> Dict[str, Any]:
    """
    Check active connections to port 5432 and port 5433.
    Query _timescaledb_catalog.hypertable to verify stock_price_history is an active hypertable.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "databases": {}
    }

    # 1. Check Local PostgreSQL (Port 5432)
    local_info = {
        "host": LOCAL_HOST,
        "port": int(LOCAL_PORT),
        "database": LOCAL_DB,
        "connected": False
    }
    try:
        start = time.perf_counter()
        local_db.execute(text("SELECT 1;"))
        latency = (time.perf_counter() - start) * 1000
        local_info["connected"] = True
        local_info["latency_ms"] = round(latency, 2)
        local_info["status"] = "online"
    except Exception as e:
        local_info["status"] = "offline_or_auth_failed"
        local_info["error"] = str(e)
        health_status["status"] = "degraded"

    health_status["databases"]["local_postgres"] = local_info

    # 2. Check TimescaleDB (Port 5433)
    timescale_info = {
        "host": TIMESCALE_HOST,
        "port": int(TIMESCALE_PORT),
        "database": TIMESCALE_DB,
        "connected": False,
        "hypertable_active": False
    }
    try:
        start = time.perf_counter()
        timescale_db.execute(text("SELECT 1;"))
        latency = (time.perf_counter() - start) * 1000
        timescale_info["connected"] = True
        timescale_info["latency_ms"] = round(latency, 2)
        timescale_info["status"] = "online"

        # Query _timescaledb_catalog.hypertable as explicitly requested
        hypertable_query = text("""
            SELECT id, schema_name, table_name 
            FROM _timescaledb_catalog.hypertable 
            WHERE table_name = 'stock_price_history';
        """)
        ht_row = timescale_db.execute(hypertable_query).fetchone()

        if ht_row:
            timescale_info["hypertable_active"] = True
            timescale_info["hypertable_id"] = ht_row[0]
            timescale_info["hypertable_schema"] = ht_row[1]
            timescale_info["hypertable_name"] = ht_row[2]
        else:
            timescale_info["hypertable_active"] = False
            timescale_info["warning"] = "Hypertable 'stock_price_history' not found in catalog."
            health_status["status"] = "degraded"

    except Exception as e:
        timescale_info["status"] = "offline"
        timescale_info["error"] = str(e)
        health_status["status"] = "degraded"

    health_status["databases"]["timescaledb"] = timescale_info
    return health_status


# ---------------------------------------------------------------------------
# 2. GET /api/timescale/prices/{ticker}
# ---------------------------------------------------------------------------
@app.get(
    "/api/timescale/prices/{ticker}",
    response_model=PriceHistoryResponse,
    summary="Fetch OHLCV stock history from TimescaleDB"
)
def get_stock_prices(
    ticker: str,
    start_date: Annotated[Optional[str], Query(description="Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[str], Query(description="End date (YYYY-MM-DD)")] = None,
    limit: Annotated[int, Query(ge=1, le=50000, description="Max rows to return")] = 1000,
    order: Annotated[str, Query(pattern="^(asc|desc|ASC|DESC)$")] = "asc",
    timescale_db: Session = Depends(get_timescale_db)
):
    """
    Fetch time-series OHLCV data directly from TimescaleDB (port 5433) sorted by price_date.
    """
    clean_ticker = ticker.strip().upper()
    order_clause = "ASC" if str(order).lower() == "asc" else "DESC"

    filters = ["ticker = :ticker"]
    params = {"ticker": clean_ticker, "limit": limit}

    if start_date:
        filters.append("price_date >= CAST(:start_date AS TIMESTAMPTZ)")
        params["start_date"] = str(start_date)

    if end_date:
        filters.append("price_date <= CAST(:end_date AS TIMESTAMPTZ)")
        params["end_date"] = str(end_date)

    where_clause = " AND ".join(filters)
    query_sql = f"""
        SELECT ticker,
               price_date,
               open_price,
               high_price,
               low_price,
               close_price,
               volume
        FROM stock_price_history
        WHERE {where_clause}
        ORDER BY price_date {order_clause}
        LIMIT :limit;
    """

    try:
        rows = timescale_db.execute(text(query_sql), params).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

    data = [
        PriceRecord(
            ticker=row[0],
            price_date=row[1].isoformat() if row[1] else "",
            open_price=float(row[2]) if row[2] is not None else None,
            high_price=float(row[3]) if row[3] is not None else None,
            low_price=float(row[4]) if row[4] is not None else None,
            close_price=float(row[5]) if row[5] is not None else None,
            volume=int(row[6]) if row[6] is not None else None
        )
        for row in rows
    ]

    return PriceHistoryResponse(
        ticker=clean_ticker,
        total_records=len(data),
        data=data
    )


# ---------------------------------------------------------------------------
# 3. GET /api/timescale/analytics/time-bucket/{ticker}
# ---------------------------------------------------------------------------
@app.get(
    "/api/timescale/analytics/time-bucket/{ticker}",
    response_model=TimeBucketResponse,
    summary="Aggregate time-bucket analytics via TimescaleDB"
)
def get_time_bucket_analytics(
    ticker: str,
    interval: Annotated[str, Query(description="Bucket duration (e.g. '7 days', '1 day', '30 days')")] = "7 days",
    start_date: Annotated[Optional[str], Query(description="Filter start date")] = None,
    end_date: Annotated[Optional[str], Query(description="Filter end date")] = None,
    timescale_db: Session = Depends(get_timescale_db)
):
    """
    Run a native TimescaleDB query using time_bucket('7 days', price_date)
    to aggregate weekly average close prices and total volumes.
    """
    clean_ticker = ticker.strip().upper()

    allowed_intervals = {"1 day", "2 days", "3 days", "5 days", "7 days", "14 days", "1 month", "30 days"}
    target_interval = str(interval).strip() if str(interval).strip() in allowed_intervals else "7 days"

    filters = ["ticker = :ticker"]
    params = {"ticker": clean_ticker}

    if start_date:
        filters.append("price_date >= CAST(:start_date AS TIMESTAMPTZ)")
        params["start_date"] = str(start_date)

    if end_date:
        filters.append("price_date <= CAST(:end_date AS TIMESTAMPTZ)")
        params["end_date"] = str(end_date)

    where_clause = " AND ".join(filters)

    query_sql = f"""
        SELECT time_bucket('{target_interval}', price_date) AS bucket,
               ROUND(AVG(close_price), 4) AS avg_close,
               SUM(volume) AS total_vol,
               ROUND(MIN(low_price), 4) AS min_p,
               ROUND(MAX(high_price), 4) AS max_p,
               COUNT(*) AS sample_count
        FROM stock_price_history
        WHERE {where_clause}
        GROUP BY bucket
        ORDER BY bucket ASC;
    """

    try:
        rows = timescale_db.execute(text(query_sql), params).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TimescaleDB time_bucket query error: {str(e)}")

    data = [
        TimeBucketRecord(
            bucket=row[0].isoformat() if row[0] else "",
            avg_close_price=float(row[1]) if row[1] is not None else None,
            total_volume=int(row[2]) if row[2] is not None else None,
            min_price=float(row[3]) if row[3] is not None else None,
            max_price=float(row[4]) if row[4] is not None else None,
            record_count=int(row[5]) if row[5] is not None else 0
        )
        for row in rows
    ]

    return TimeBucketResponse(
        ticker=clean_ticker,
        interval=target_interval,
        total_buckets=len(data),
        data=data
    )
