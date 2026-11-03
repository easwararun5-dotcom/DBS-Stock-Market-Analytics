"""
sec06_er_schema.py - ER Diagram, Relational Schema Specifications, and Diagrams
"""

import os
from docx import Document
from docx.shared import Inches
from report_utils import (
    add_h1, add_h2, add_h3, add_body_p, add_bullet_p, add_callout_box,
    add_figure, create_styled_table
)

def build_er_and_relational_schema(doc: Document):
    """Renders Section 7: ER Diagram and Relational Schema Specifications."""
    add_h1(doc, "7. Database Design: ER Diagram and Relational Schema")
    
    add_body_p(
        doc,
        "A rigorous conceptual, logical, and physical database design was executed following standard relational database design methodologies (Elmasri & Navathe). This section details the conceptual Entity-Relationship (ER) model, visualizes both the original design artifacts and publication-grade schema layouts, and specifies the complete relational schema across all 16 core tables."
    )
    
    add_h2(doc, "7.1 Conceptual ER Model and Cardinality Ratios")
    add_body_p(
        doc,
        "The conceptual domain is modeled around three interconnected subsystems: Master Market Taxonomy, Time-Series Quotations, and Transactional Multi-Portfolio Accounting:"
    )
    add_bullet_p(
        doc,
        " Represents macro-economic industry classifications. Relationship with COMPANY is 1-to-Many (1:N), where one sector contains multiple companies, but every company belongs to exactly one mandatory sector (total participation).",
        bold_prefix="SECTOR Entity: "
    )
    add_bullet_p(
        doc,
        " Represents enterprise equities identified by unique primary key ticker. Relationship with DAILY_PRICE_HISTORY is 1-to-Many (1:N), where one company has hundreds of chronological price points. Relationship with CORPORATE_ACTION is 1-to-Many (1:N).",
        bold_prefix="COMPANY Entity: "
    )
    add_bullet_p(
        doc,
        " Represents authenticated traders. Relationship with USER_PORTFOLIO is 1-to-Many (1:N), allowing a single user to maintain multiple distinct investment portfolios (e.g., 'Long Term Growth' vs. 'High Risk Momentum').",
        bold_prefix="APP_USER Entity: "
    )
    add_bullet_p(
        doc,
        " Represents an isolated virtual trading ledger. Maintains cash balance, initial funding, and realized gains. Relationship with PORTFOLIO_HOLDING is 1-to-Many (1:N) and PORTFOLIO_TRANSACTION is 1-to-Many (1:N).",
        bold_prefix="USER_PORTFOLIO Entity: "
    )
    add_bullet_p(
        doc,
        " Represents aggregated equity positions. Identified by composite primary key (portfolio_id, ticker). Relationship with USER_PORTFOLIO is Many-to-1 (N:1) and with COMPANY is Many-to-1 (N:1).",
        bold_prefix="PORTFOLIO_HOLDING Entity: "
    )
    add_bullet_p(
        doc,
        " Represents immutable executed trade orders (BUY/SELL). Identified by transaction_id. Carries foreign keys portfolio_id and ticker.",
        bold_prefix="PORTFOLIO_TRANSACTION Entity: "
    )
    
    add_h2(doc, "7.2 Original Conceptual ER Diagram Artifacts")
    add_body_p(
        doc,
        "The conceptual model was initially developed through iterative whiteboard and collaborative design sessions. The authentic design sheets are preserved below to demonstrate the chronological evolution from conceptual entity modeling to relational implementation:"
    )
    
    img_sheet1 = "docs/er-diagram/WhatsApp Image 2026-09-01 at 16.59.03 (1).jpeg"
    img_sheet2 = "docs/er-diagram/WhatsApp Image 2026-09-01 at 16.59.14 (1).jpeg"
    img_sheet3 = "docs/er-diagram/WhatsApp Image 2026-09-01 at 16.59.21 (1).jpeg"
    
    add_figure(
        doc,
        img_sheet1,
        "Figure 2: Conceptual ER Diagram (Design Sheet 1) — User, Portfolio, Holdings, and Transaction Relationships.",
        width=Inches(3.8)
    )
    add_figure(
        doc,
        img_sheet2,
        "Figure 3: Conceptual ER Diagram (Design Sheet 2) — Company, Sector Taxonomy, and Market Quotation Mappings.",
        width=Inches(3.8)
    )
    add_figure(
        doc,
        img_sheet3,
        "Figure 4: Conceptual ER Diagram (Design Sheet 3) — Technical Indicators, ML Feature Store, and Risk Analysis.",
        width=Inches(3.8)
    )
    
    add_h2(doc, "7.3 Relational Schema Layout and Inter-Table Relationships")
    add_body_p(
        doc,
        "The conceptual ER model was translated into an enterprise relational schema. Figure 5 depicts the comprehensive relational architecture, mapping primary-to-foreign key connections, table classifications, and database host boundaries:"
    )
    
    fig_schema = "docs/report-preparation/figures/relational_schema_layout.png"
    add_figure(
        doc,
        fig_schema,
        "Figure 5: Publication-Grade Relational Schema Layout illustrating 16 Normalized Base Tables, Primary/Foreign Key Connections, and Dual Database Host Separation (PostgreSQL Port 5435 vs. TimescaleDB Port 5434).",
        width=Inches(6.2)
    )
    
    add_h2(doc, "7.4 Relational Schema Specifications (16 Base Tables)")
    add_body_p(
        doc,
        "The physical database implementation comprises 16 base relational tables, meticulously constrained with primary keys, composite keys, foreign key cascading semantics, unique indexes, and domain checks:"
    )
    
    headers = ["Table Name", "Primary Key", "Foreign Keys & Target Tables", "Key Constraints & Check Rules", "Storage Host / DB"]
    schema_data = [
        ["sector", "sector_id", "None", "sector_name UNIQUE, NOT NULL", "PostgreSQL (5435)"],
        ["company", "ticker (VARCHAR(10))", "sector_id -> sector(sector_id)", "name NOT NULL, is_active DEFAULT TRUE", "PostgreSQL (5435)"],
        ["daily_price_history", "(ticker, date)", "ticker -> company(ticker)", "TimescaleDB Hypertable (360d chunk), volume >= 0", "TimescaleDB (5434) & PG"],
        ["corporate_action", "action_id", "ticker -> company(ticker)", "action_type IN ('DIVIDEND', 'SPLIT'), value > 0", "PostgreSQL (5435)"],
        ["stock_summary", "ticker", "ticker -> company(ticker)", "avg_volume >= 0, 52w_high >= 52w_low", "PostgreSQL (5435)"],
        ["market_index", "index_id", "None", "symbol UNIQUE, name NOT NULL", "PostgreSQL (5435)"],
        ["app_user", "user_id", "None", "email UNIQUE, username UNIQUE, role IN ('USER','ADMIN')", "PostgreSQL (5435)"],
        ["user_portfolio", "portfolio_id", "user_id -> app_user(user_id) ON DELETE CASCADE", "cash_balance >= 0, UNIQUE(user_id, portfolio_name)", "PostgreSQL (5435)"],
        ["portfolio_holding", "(portfolio_id, ticker)", "portfolio_id -> user_portfolio, ticker -> company", "quantity >= 0, avg_buy_price >= 0 (Pure 3NF)", "PostgreSQL (5435)"],
        ["portfolio_transaction", "transaction_id", "portfolio_id -> user_portfolio, ticker -> company", "transaction_type IN ('BUY', 'SELL'), quantity > 0, price > 0", "PostgreSQL (5435)"],
        ["transaction_audit_log", "audit_id", "None (Immutable Log)", "operation IN ('INSERT', 'UPDATE', 'DELETE')", "PostgreSQL (5435)"],
        ["portfolio_risk_analysis", "analysis_id", "portfolio_id -> user_portfolio(portfolio_id)", "sharpe_ratio, max_drawdown, calculated_at", "PostgreSQL (5435)"],
        ["portfolio_risk_sector_allocation", "allocation_id", "analysis_id -> portfolio_risk_analysis(analysis_id)", "allocation_percentage BETWEEN 0 AND 100 (1NF Decomp)", "PostgreSQL (5435)"],
        ["technical_indicator", "indicator_id", "ticker -> company(ticker)", "UNIQUE(ticker, calculation_date, indicator_name)", "PostgreSQL (5435)"],
        ["ml_model_registry", "model_id", "None", "model_name, version, training_accuracy, is_active", "PostgreSQL (5435)"],
        ["ml_feature_store", "feature_id", "ticker -> company(ticker)", "UNIQUE(ticker, feature_date), 20 numerical features", "PostgreSQL (5435)"]
    ]
    create_styled_table(
        doc,
        headers,
        schema_data,
        [Inches(1.8), Inches(1.3), Inches(1.8), Inches(1.8), Inches(1.3)]
    )
    
    add_callout_box(
        doc,
        "Schema Purity Highlight: Notice that 'portfolio_holding' uses composite primary key (portfolio_id, ticker) and contains NO redundant user_id. In Migration 05, user_id was formally dropped to eliminate a transitive dependency (portfolio_id -> user_id), achieving pure 3NF compliance.",
        title="SCHEMA PURITY VERIFICATION"
    )

