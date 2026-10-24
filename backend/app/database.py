import os
import urllib.parse
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

Base = declarative_base()

# ---------------------------------------------------------------------------
# 1. Local PostgreSQL Engine Configuration (Port 5432 - stock_market_db)
# ---------------------------------------------------------------------------
LOCAL_HOST = os.getenv("LOCAL_PG_HOST", os.getenv("PGHOST", "localhost"))
LOCAL_PORT = os.getenv("LOCAL_PG_PORT", os.getenv("PGPORT", "5432"))
LOCAL_DB = os.getenv("LOCAL_PG_DB", os.getenv("PGDATABASE", "stock_market_db"))
LOCAL_USER = os.getenv("LOCAL_PG_USER", os.getenv("PGUSER", "postgres"))
LOCAL_PASSWORD = os.getenv("LOCAL_PG_PASSWORD", os.getenv("PGPASSWORD", "postgres"))

_encoded_local_password = urllib.parse.quote_plus(LOCAL_PASSWORD)
LOCAL_DATABASE_URL = (
    f"postgresql+psycopg2://{LOCAL_USER}:{_encoded_local_password}@{LOCAL_HOST}:{LOCAL_PORT}/{LOCAL_DB}"
)

engine_local = create_engine(
    LOCAL_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)
SessionLocalDB = sessionmaker(autocommit=False, autoflush=False, bind=engine_local)


# ---------------------------------------------------------------------------
# 2. TimescaleDB Engine Configuration (Port 5433 - stock_timescale_db)
# ---------------------------------------------------------------------------
TIMESCALE_HOST = os.getenv("TIMESCALE_PG_HOST", "localhost")
TIMESCALE_PORT = os.getenv("TIMESCALE_PG_PORT", "5433")
TIMESCALE_DB = os.getenv("TIMESCALE_PG_DB", "stock_timescale_db")
TIMESCALE_USER = os.getenv("TIMESCALE_PG_USER", "postgres")
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PG_PASSWORD", "postgres")

_encoded_timescale_password = urllib.parse.quote_plus(TIMESCALE_PASSWORD)
TIMESCALE_DATABASE_URL = (
    f"postgresql+psycopg2://{TIMESCALE_USER}:{_encoded_timescale_password}@{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
)

engine_timescale = create_engine(
    TIMESCALE_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionTimescaleDB = sessionmaker(autocommit=False, autoflush=False, bind=engine_timescale)


# ---------------------------------------------------------------------------
# 3. FastAPI Dependency Providers
# ---------------------------------------------------------------------------
def get_local_db() -> Generator[Session, None, None]:
    """Dependency provider for local PostgreSQL session (Port 5432)."""
    db = SessionLocalDB()
    try:
        yield db
    finally:
        db.close()


def get_timescale_db() -> Generator[Session, None, None]:
    """Dependency provider for TimescaleDB session (Port 5433)."""
    db = SessionTimescaleDB()
    try:
        yield db
    finally:
        db.close()
