"""
Database configuration for DBS Stock Market Analytics.

Connects to the TimescaleDB instance (stock_timescale_db) which holds all project
tables. The Docker container exposes PostgreSQL internally on port 5432 and maps to
host port 5433. When running the FastAPI server on the Windows host, we connect
through localhost:5433.

All credentials are loaded from environment variables (with safe defaults for
local development). Never hardcode passwords in source.
"""

import os
import urllib.parse
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Load .env from the project root (two levels up from this file)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

Base = declarative_base()

# ---------------------------------------------------------------------------
# Database connection settings
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "stock_timescale_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

_encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{_encoded_password}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
