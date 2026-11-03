"""
sec03_existing_systems.py - Existing Systems Research, Comparative Matrix, and Audit
"""

from docx import Document
from docx.shared import Inches
from report_utils import (
    add_h1, add_h2, add_h3, add_body_p, add_bullet_p, add_callout_box, create_styled_table
)

def build_existing_systems(doc: Document):
    """Renders Section 4: Existing Systems Research (URLs, Analysis & Comparative Audit)."""
    add_h1(doc, "4. Existing Systems Research and Comparative Audit")
    
    add_body_p(
        doc,
        "To establish a rigorous technical benchmark for the proposed Stock Market Analytics and Portfolio Management System, four industry-leading financial platforms were evaluated. Each platform represents a distinct architectural paradigm in financial data management, ranging from proprietary charting engines to institutional retail brokerages and academic quantitative simulators."
    )
    
    add_h2(doc, "4.1 Platform 1: TradingView")
    add_bullet_p(doc, "https://www.tradingview.com/", bold_prefix="Official Platform URL: ")
    add_bullet_p(
        doc,
        "TradingView is the global industry benchmark for browser-based interactive financial charting, technical indicator visualization, and social investing networks. It provides millisecond-level responsive charting across thousands of global tickers, supporting proprietary scripting (Pine Script) and custom overlay indicators.",
        bold_prefix="Core Architectural Strengths: "
    )
    add_bullet_p(
        doc,
        "TradingView relies on a proprietary, closed-source time-series database architecture optimized exclusively for streaming candle data to client canvases. It does not expose its underlying relational schema or permit relational joins between user trading ledgers and historical prices. Furthermore, its paper trading facility is an isolated simulation sandbox decoupled from customizable relational multi-portfolio accounting ledgers.",
        bold_prefix="DBMS & Architectural Limitations: "
    )
    add_bullet_p(
        doc,
        "Capture the primary interactive candlestick chart interface showing technical overlays (MACD, RSI, Bollinger Bands) alongside the simulated 'Paper Trading' account panel located at the bottom docking bar.",
        bold_prefix="Recommended Screenshot Capture: "
    )
    
    add_h2(doc, "4.2 Platform 2: Yahoo Finance")
    add_bullet_p(doc, "https://finance.yahoo.com/", bold_prefix="Official Platform URL: ")
    add_bullet_p(
        doc,
        "Yahoo Finance represents one of the most widely visited consumer financial portals globally. It aggregates market quotes, fundamental corporate financial statements (10-K/10-Q), consensus analyst recommendations, and historical daily price downloads (CSV exports) for broad retail audiences.",
        bold_prefix="Core Architectural Strengths: "
    )
    add_bullet_p(
        doc,
        "Yahoo Finance utilizes a heavily cached, read-oriented REST API and Content Delivery Network (CDN) distribution tier. However, it lacks native transactional paper trading mechanics. Its 'Watchlist' and 'My Portfolio' features are purely observational; they do not enforce double-entry cash accounting, pessimistic concurrency control, or order execution lifecycle constraints.",
        bold_prefix="DBMS & Architectural Limitations: "
    )
    add_bullet_p(
        doc,
        "Capture the historical data table tab showing daily OHLCV rows for an enterprise ticker (e.g., AAPL), demonstrating static tabular retrieval without dynamic time-bucket aggregation.",
        bold_prefix="Recommended Screenshot Capture: "
    )
    
    add_h2(doc, "4.3 Platform 3: Zerodha Kite & Console")
    add_bullet_p(doc, "https://kite.zerodha.com/ (Trading) and https://console.zerodha.com/ (Reporting)", bold_prefix="Official Platform URL: ")
    add_bullet_p(
        doc,
        "Zerodha is India's largest retail brokerage by volume. Its technology stack represents an enterprise design: Kite handles high-concurrency Order Routing and Execution (OLTP), while Console provides in-depth trade reporting, capital gains tax calculation, and portfolio analytics (OLAP). Zerodha prominently utilizes PostgreSQL for its relational persistence.",
        bold_prefix="Core Architectural Strengths: "
    )
    add_bullet_p(
        doc,
        "Zerodha enforces a strict, rigid physical separation between its real-time OLTP order books and next-day OLAP reporting databases (which are refreshed via overnight batch ETL pipelines). Consequently, retail traders cannot perform on-demand, arbitrary historical time-bucket queries on intraday positions. Furthermore, it requires live Demat accounts and capital funding, offering no zero-risk paper trading sandbox for algorithmic exploration.",
        bold_prefix="DBMS & Architectural Limitations: "
    )
    add_bullet_p(
        doc,
        "Capture the Kite Holdings interface showing real-time P&L, matched against the Console P&L breakdown showing historical tax lots and tradebook transaction histories.",
        bold_prefix="Recommended Screenshot Capture: "
    )
    
    add_h2(doc, "4.4 Platform 4: Portfolio Visualizer")
    add_bullet_p(doc, "https://www.portfoliovisualizer.com/", bold_prefix="Official Platform URL: ")
    add_bullet_p(
        doc,
        "Portfolio Visualizer is a quantitative modeling platform renowned for Monte Carlo simulations, Fama-French factor analysis, asset allocation backtesting, and mean-variance portfolio optimization.",
        bold_prefix="Core Architectural Strengths: "
    )
    add_bullet_p(
        doc,
        "The platform operates on a rigid batch-computation model where users configure static backtest parameters and execute heavy server-side mathematical routines. It lacks a dynamic, real-time relational transactional ledger for active simulated order placement and features a legacy, non-interactive user interface.",
        bold_prefix="DBMS & Architectural Limitations: "
    )
    add_bullet_p(
        doc,
        "Capture the 'Backtest Portfolio Asset Allocation' summary page displaying the historical return growth chart, Sharpe ratio, and annual drawdown matrix.",
        bold_prefix="Recommended Screenshot Capture: "
    )
    
    add_h2(doc, "4.5 Comparative Analysis Matrix")
    add_body_p(
        doc,
        "The following matrix summarizes the architectural, database, and functional distinctions between the existing platforms and the proposed Stock Market Analytics System:"
    )
    
    headers = [
        "Architectural Dimension",
        "TradingView",
        "Yahoo Finance",
        "Zerodha Kite / Console",
        "Portfolio Visualizer",
        "Proposed System"
    ]
    matrix_data = [
        [
            "Database Architecture",
            "Proprietary TSDB + Client Cache",
            "Cached NoSQL / CDN Data Lake",
            "PostgreSQL OLTP + Batch Data Warehouse",
            "Batch RDBMS / In-Memory Compute",
            "Decoupled PostgreSQL 18.4 + TimescaleDB 2.31.0"
        ],
        [
            "Time-Series Partitioning",
            "Internal Chunking (Closed)",
            "None (Pre-aggregated blobs)",
            "Partitioned Tables (Nightly ETL)",
            "Flat Memory Arrays",
            "Automated Hypertables (360-Day Chunks, 28 Chunks)"
        ],
        [
            "Transactional Model",
            "Simulated Sandbox (No ACID)",
            "None (Static Watchlists)",
            "Strict Distributed ACID / OMS",
            "Static Batch State",
            "Strict ACID with SELECT FOR UPDATE Row Locks"
        ],
        [
            "Paper Trading Engine",
            "Basic Single-Account Mock",
            "None",
            "None (Requires Real Capital)",
            "None (Historical Backtest Only)",
            "Full Multi-Portfolio Ledger with Cash Bounds"
        ],
        [
            "Schema Normalization",
            "Proprietary / Unknown",
            "Denormalized Key-Value Blobs",
            "3NF Enterprise Relational",
            "Proprietary Tabular",
            "Verified Pure 3NF / BCNF (16 Relational Tables)"
        ],
        [
            "Integrated Predictive ML",
            "Pine Script Indicators Only",
            "External Analyst Consensuses",
            "None",
            "Factor Regressions (Statistical)",
            "HistGradientBoosting (20 Tech Features, 54.1% Acc)"
        ],
        [
            "Extensibility & Open Source",
            "Closed Commercial Platform",
            "Closed Commercial Platform",
            "Proprietary Enterprise",
            "Closed Commercial Platform",
            "100% Fully Documented, Auditable Open Architecture"
        ]
    ]
    create_styled_table(
        doc,
        headers,
        matrix_data,
        [Inches(1.2), Inches(1.0), Inches(1.0), Inches(1.1), Inches(1.0), Inches(1.2)]
    )
    
    add_callout_box(
        doc,
        "Comparative Finding: While existing platforms excel within isolated domains (TradingView for charting, Zerodha for execution, Portfolio Visualizer for statistics), the proposed system is unique in providing an open, academically provable hybrid database architecture that unites automated time-series hypertable partitioning with ACID row-locked portfolio accounting.",
        title="BENCHMARK SYNTHESIS"
    )
    
    # Page break after Section 4
    doc.add_page_break()
