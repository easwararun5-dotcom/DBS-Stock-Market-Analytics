"""
Dual Database configuration for DBS Stock Market Analytics.

Maintains two independent database connections:
1. Connection A (Relational): Original PostgreSQL instance holding all 14 project tables
   (companies, sectors, fundamentals, summaries, users, portfolios, etc.) on port 5435.
2. Connection B (Time-Series): TimescaleDB instance running in Docker on port 5434,
   specifically optimized for hypertable-backed time-series price data and aggregations.

All credentials and ports are loaded from environment variables with safe defaults.
Never hardcode passwords or sensitive credentials in source code.
"""

import os
import urllib.parse
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Load .env from project root (two levels up from this file)
_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(_env_path)

Base = declarative_base()

# ---------------------------------------------------------------------------
# Connection A: PostgreSQL (Relational Database)
# ---------------------------------------------------------------------------
POSTGRES_HOST = os.getenv("POSTGRES_HOST", os.getenv("PGHOST", "localhost"))
POSTGRES_PORT = os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5435"))
POSTGRES_DB = os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "stock_market_db"))
POSTGRES_USER = os.getenv("POSTGRES_USER", os.getenv("PGUSER", "easwarap"))
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", ""))

if POSTGRES_PASSWORD:
    _pg_encoded_pw = urllib.parse.quote_plus(POSTGRES_PASSWORD)
    POSTGRES_DATABASE_URL = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{_pg_encoded_pw}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
else:
    POSTGRES_DATABASE_URL = (
        f"postgresql+psycopg2://{POSTGRES_USER}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

engine_relational = create_engine(
    POSTGRES_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocalRelational = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_relational
)


# ---------------------------------------------------------------------------
# Connection B: TimescaleDB (Time-Series Database)
# ---------------------------------------------------------------------------
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST", os.getenv("TS_HOST", "localhost"))
TIMESCALE_PORT = os.getenv("TIMESCALE_PORT", os.getenv("TS_PORT", "5434"))
TIMESCALE_DB = os.getenv("TIMESCALE_DB", os.getenv("TS_DB", "stock_timescale_db"))
TIMESCALE_USER = os.getenv("TIMESCALE_USER", os.getenv("TS_USER", "postgres"))
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PASSWORD", os.getenv("TS_PASSWORD", "postgres"))

_ts_encoded_pw = urllib.parse.quote_plus(TIMESCALE_PASSWORD)
TIMESCALE_DATABASE_URL = (
    f"postgresql+psycopg2://{TIMESCALE_USER}:{_ts_encoded_pw}"
    f"@{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
)

engine_timescale = create_engine(
    TIMESCALE_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocalTimescale = sessionmaker(
    autocommit=False, autoflush=False, bind=engine_timescale
)


# ---------------------------------------------------------------------------
# FastAPI Dependency Injections
# ---------------------------------------------------------------------------
def get_relational_db() -> Generator[Session, None, None]:
    """Yields a database session connected to the relational PostgreSQL database."""
    db = SessionLocalRelational()
    try:
        yield db
    finally:
        db.close()


def get_timescale_db() -> Generator[Session, None, None]:
    """Yields a database session connected to the time-series TimescaleDB database."""
    db = SessionLocalTimescale()
    try:
        yield db
    finally:
        db.close()


# Backward compatibility aliases
get_db = get_relational_db
engine = engine_relational
SessionLocal = SessionLocalRelational
DB_HOST = POSTGRES_HOST
DB_PORT = POSTGRES_PORT
DB_NAME = POSTGRES_DB
