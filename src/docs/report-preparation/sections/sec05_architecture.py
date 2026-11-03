"""
sec05_architecture.py - Proposed System Architecture, Diagrams, and Routing
"""

import os
from docx import Document
from docx.shared import Inches
from report_utils import (
    add_h1, add_h2, add_h3, add_body_p, add_bullet_p, add_callout_box,
    add_figure, create_styled_table
)

def build_system_architecture(doc: Document):
    """Renders Section 6: Proposed System Architecture and Routing Matrix."""
    add_h1(doc, "6. Proposed System Architecture")
    
    add_body_p(
        doc,
        "The Stock Market Analytics and Portfolio Management System is structured around a decoupled 3-Tier Architecture. By isolating the Presentation Layer, Application Processing Layer, and Data Persistence Layer, the system achieves horizontal scalability, strict security boundaries, and modular maintainability. Crucially, the Data Layer is further bifurcated into two purpose-built database engines to eliminate the trade-off between transactional consistency and analytical streaming."
    )
    
    # Embed Figure 1: Architecture Diagram
    fig_path = "docs/report-preparation/figures/architecture_diagram.png"
    add_figure(
        doc,
        fig_path,
        "Figure 1: High-Performance 3-Tier Decoupled Architecture showing React 19 Frontend, FastAPI Application Layer, and Dual Database Tier (PostgreSQL 18.4 and TimescaleDB 2.31.0).",
        width=Inches(6.0)
    )
    
    add_h2(doc, "6.1 Architectural Tier Breakdown")
    
    add_h3(doc, "6.1.1 Client Tier (Presentation Layer)")
    add_body_p(
        doc,
        "The client tier is implemented as a modern Single-Page Application (SPA) utilizing React 19.0.0 and bundled with Vite 6.0.5. Styled using Tailwind CSS with Lucide React iconography, the frontend delivers a responsive, desktop-class trading terminal experience. State management handles interactive chart zoom/pan, real-time portfolio P&L updates, dynamic stock filtering across sectors, and simulated buy/sell order modal dialogs. Client-side HTTP requests communicate asynchronously with the backend REST API via standard JSON payloads."
    )
    
    add_h3(doc, "6.1.2 Application Tier (FastAPI & Business Logic Layer)")
    add_body_p(
        doc,
        "The application processing tier is powered by FastAPI 0.115.0 running on Python 3.12 / 3.14. FastAPI was chosen for its high-throughput asynchronous request handling (built on Starlette and Uvicorn) and strict type validation using Pydantic v2 schemas. This tier encapsulates:"
    )
    add_bullet_p(doc, "Routes incoming requests to either PostgreSQL or TimescaleDB based on query intent.", bold_prefix="Intelligent Database Router: ")
    add_bullet_p(doc, "Coordinates row-level pessimistic locking, balance verifications, and multi-table updates within atomic transaction contexts.", bold_prefix="Paper Trading Execution Engine: ")
    add_bullet_p(doc, "Calculates moving averages (SMA-20, SMA-50), Relative Strength Index (RSI-14), Moving Average Convergence Divergence (MACD), Bollinger Bands, and Average True Range (ATR).", bold_prefix="Technical Indicator Service: ")
    add_bullet_p(doc, "Extracts 20 feature dimensions from historical market data and executes inference using a pre-trained scikit-learn HistGradientBoosting model.", bold_prefix="Machine Learning Inference Pipeline: ")
    
    add_h3(doc, "6.1.3 Data Persistence Tier (Decoupled Dual-Database Architecture)")
    add_body_p(
        doc,
        "The core innovation of the proposed design resides in its dual-database persistence tier, which physically separates stateful transactional entities from voluminous append-only market quotations:"
    )
    add_bullet_p(
        doc,
        "Operates on host port 5435 (database: stock_market_db). Serves as the primary system of record for all 16 normalized relational base tables and 7 analytical views. Manages user authentication, multi-portfolio ledgers, holdings, cash balances, executed trade orders, and audit logs under strict ACID guarantees.",
        bold_prefix="Relational Transactional Core (PostgreSQL 18.4): "
    )
    add_bullet_p(
        doc,
        "Operates on host port 5434 (database: stock_timescale_db) via an official Docker container running TimescaleDB 2.31.0 on PostgreSQL 17.11. Configured with a partitioned hypertable daily_price_history spanning 28 discrete chunks across 360-day intervals, storing 287,310 price records and 1,653 corporate actions. Supports native time_bucket() analytical aggregations with zero index bloat.",
        bold_prefix="Time-Series Hypertable Engine (TimescaleDB 2.31.0): "
    )
    
    add_h2(doc, "6.2 Active Database Query Routing Matrix")
    add_body_p(
        doc,
        "To ensure verifiable execution, the FastAPI application implements dynamic database routing across its REST endpoints. The following matrix details the active routing rules, target database engines, underlying tables, and fallback behavior:"
    )
    
    headers = ["API Route", "Method", "Engine", "Target DB", "Primary Tables", "Failover Behavior"]
    routing_data = [
        ["/api/health", "GET", "Both Pools", "Both Engines", "Dual DB ping check", "Reports individual status for PG and TimescaleDB."],
        ["/api/dashboard", "GET", "engine_timescale", "TimescaleDB (5434)", "daily_price_history", "Active Fallback: If 5434 unreachable, queries PG 5435."],
        ["/api/companies", "GET", "engine_pg", "PostgreSQL (5435)", "company, sector", "None (PostgreSQL is required master of record)."],
        ["/api/prices/{ticker}", "GET", "engine_timescale", "TimescaleDB (5434)", "daily_price_history", "Fails fast if TimescaleDB container is stopped."],
        ["/api/analytics/time-bucket/{ticker}", "GET", "engine_timescale", "TimescaleDB (5434)", "daily_price_history", "Requires native TimescaleDB extension on port 5434."],
        ["/api/portfolios", "GET / POST", "engine_pg", "PostgreSQL (5435)", "user_portfolio", "ACID transactional session on PostgreSQL."],
        ["/api/trading/buy", "POST", "engine_pg", "PostgreSQL (5435)", "user_portfolio, holdings", "Enforces SELECT FOR UPDATE row-level pessimistic locks."],
        ["/api/trading/sell", "POST", "engine_pg", "PostgreSQL (5435)", "user_portfolio, holdings", "Enforces row locks and fires consistency triggers."],
        ["/api/ml/predict/{ticker}", "GET", "engine_timescale", "TimescaleDB (5434)", "daily_price_history", "Extracts historical price series for ML inference."],
        ["/api/risk-analysis/{id}", "GET", "engine_pg", "PostgreSQL (5435)", "risk_analysis, sector_alloc", "Reads normalized risk and sector allocations."]
    ]
    # Total width: 1.4 + 0.6 + 1.1 + 1.1 + 1.1 + 1.2 = 6.50 in
    create_styled_table(
        doc,
        headers,
        routing_data,
        [Inches(1.4), Inches(0.6), Inches(1.1), Inches(1.1), Inches(1.1), Inches(1.2)]
    )
    
    add_callout_box(
        doc,
        "Architectural Verification: The application does NOT merely treat TimescaleDB as passive storage. TimescaleDB is actively queried for historical prices, dynamic time-bucket rollups, and ML feature extraction. Concurrently, all transactional paper trading and portfolio ledgers execute exclusively on PostgreSQL with pessimistic concurrency control.",
        title="DUAL ROUTING VERIFICATION"
    )
    
    # Page break after Section 6
    doc.add_page_break()
