"""
sec02_intro_problem.py - Introduction, Problem Statement, Objectives, and Scope
"""

from docx import Document
from report_utils import (
    add_h1, add_h2, add_h3, add_body_p, add_bullet_p, add_callout_box
)

def build_intro_problem_objectives(doc: Document):
    """Renders Section 3: Introduction, Problem Statement, Objectives, and Scope."""
    add_h1(doc, "3. Introduction, Problem Statement, Objectives, and Scope")
    
    add_h2(doc, "3.1 Introduction")
    add_body_p(
        doc,
        "The digital transformation of global capital markets over the past decade has democratized equity trading and portfolio management for retail investors, algorithmic researchers, and academic institutions. Contemporary financial applications require an unprecedented confluence of analytical responsiveness, historical depth, and transactional precision. Users expect real-time interactive technical charting, instant moving-average rollups over multi-decade horizons, algorithmic signal generation, and simulated 'paper trading' capabilities that mimic real-world brokerages without exposing capital to financial risk."
    )
    add_body_p(
        doc,
        "Underpinning these capabilities is a rigorous data management requirement. Financial market data exhibits dual characteristics: on one hand, market quotations (Open, High, Low, Close, Volume - OHLCV) represent append-only, chronologically ordered time-series data generated at immense volumes. On the other hand, user portfolios, cash balances, equity positions, execution orders, and compliance audit trails represent stateful, highly relational entities governed by strict ACID (Atomicity, Consistency, Isolation, Durability) guarantees."
    )
    add_body_p(
        doc,
        "Under computer science pedagogy and database systems curricula (such as BACSE202 - Database Management Systems), students are traditionally exposed to standard relational paradigms through simplified business schemas. However, real-world financial systems demand an advanced mastery of relational schema design, third and Boyce-Codd normal forms, complex constraints, triggers, pessimistic concurrency locking, and hybrid integration with specialized time-series database engines. This project serves as an end-to-end academic bridge, demonstrating how enterprise-grade database principles are applied to engineer a resilient, scalable, and mathematically normalized Stock Market Analytics and Portfolio Management System."
    )
    
    add_h2(doc, "3.2 Problem Statement")
    add_body_p(
        doc,
        "Traditional application architectures attempting to manage both high-frequency time-series market feeds and transactional financial ledgers within a single standard relational database encounter three severe engineering bottlenecks:"
    )
    
    add_bullet_p(
        doc,
        "In standard relational engines like vanilla PostgreSQL or MySQL, storing millions of daily historical price records creates massive B-tree indexes on compound keys (e.g., (ticker, date)). As index sizes exceed RAM memory limits, random disk page writes degrade insertion speeds exponentially, while analytical range queries suffer from extensive index scans across non-contiguous storage pages.",
        bold_prefix="Index Bloat and Write Degradation in Flat Relational Tables: "
    )
    add_bullet_p(
        doc,
        "Retail paper trading platforms frequently exhibit race conditions during simulated market orders. In the absence of strict pessimistic row-level locking (SELECT ... FOR UPDATE) and database-level check constraints, rapid asynchronous requests can cause double-spending of wallet cash or overselling of shares beyond owned quantities, leaving ledger balances inconsistent.",
        bold_prefix="Transactional Concurrency Anomalies and Race Conditions: "
    )
    add_bullet_p(
        doc,
        "Ad-hoc financial platforms frequently violate 3NF and BCNF by storing denormalized aggregates, redundant company descriptions, or non-atomic JSON allocations within transactional tables. Such design compromises lead to classic update, insertion, and deletion anomalies when corporate actions (e.g., stock splits, name changes, or sector reclassifications) occur.",
        bold_prefix="Denormalization Anomalies and Schema Degradation: "
    )
    
    add_callout_box(
        doc,
        "Problem Statement Summary: How can an academic financial platform decouple high-velocity time-series market quotations from transactional portfolio accounting, ensuring sub-15ms analytical aggregations on 280,000+ records while guaranteeing zero-concurrency race conditions and pure BCNF relational integrity?",
        title="FORMAL PROBLEM STATEMENT"
    )
    
    add_h2(doc, "3.3 Project Objectives")
    add_body_p(
        doc,
        "To systematically address the stated problem, this project defines six core academic and architectural objectives:"
    )
    add_bullet_p(
        doc,
        "Construct a relational schema spanning 16 base tables and 7 analytical views, verified to satisfy Third Normal Form (3NF) and Boyce-Codd Normal Form (BCNF), with formal candidate key proofs and foreign key integrity rules.",
        bold_prefix="Objective 1 (Relational Normalization): "
    )
    add_bullet_p(
        doc,
        "Deploy TimescaleDB with hypertable partitioning across 360-day intervals, eliminating standard B-tree index degradation and enabling native time_bucket() analytical rollups over 287,310 historical price records.",
        bold_prefix="Objective 2 (Time-Series Hypertable Partitioning): "
    )
    add_bullet_p(
        doc,
        "Implement row-level pessimistic locking (SELECT ... FOR UPDATE) within multi-table ACID transaction blocks, supplemented by database triggers that mathematically prevent overselling and log every mutation into an immutable audit table.",
        bold_prefix="Objective 3 (Concurrency-Safe Paper Trading Engine): "
    )
    add_bullet_p(
        doc,
        "Develop a high-performance REST API tier utilizing FastAPI and SQLAlchemy, featuring dual connection pools, intelligent database query routing, and automated fallback mechanisms to maintain system availability.",
        bold_prefix="Objective 4 (Dual-Engine Database Connectivity): "
    )
    add_bullet_p(
        doc,
        "Build a machine learning pipeline that extracts 20 technical indicators from the historical database to train an optimized HistGradientBoostingClassifier for directional next-day price forecasting.",
        bold_prefix="Objective 5 (Predictive Analytics Integration): "
    )
    add_bullet_p(
        doc,
        "Validate the end-to-end architecture through comprehensive automated unit tests, transaction lifecycle scripts, schema constraint audits, and frontend performance profiling.",
        bold_prefix="Objective 6 (Empirical Verification and Validation): "
    )
    
    add_h2(doc, "3.4 Project Scope")
    add_body_p(
        doc,
        "The boundaries of this project are strictly delineated between implemented capabilities and deferred enterprise features:"
    )
    add_bullet_p(
        doc,
        "Full relational ledger for multi-portfolio management; automated cash accounting ($100,000 initial virtual funding); real-time portfolio valuation; technical indicator computation (SMA, EMA, RSI, MACD, Bollinger Bands); native time_bucket OHLCV aggregations; automated audit logging; and machine learning inference.",
        bold_prefix="In-Scope Core Capabilities: "
    )
    add_bullet_p(
        doc,
        "Live real-time market WebSocket streaming (historical dataset spanning 5 years across 49 enterprise equities is utilized); external payment gateway integration (simulated paper cash is used); and multi-broker FIX protocol connectivity.",
        bold_prefix="Out-of-Scope Enterprise Extensions: "
    )
    
    # Page break after Section 3
    doc.add_page_break()
