"""
sec01_title_abstract.py - Title Page, Academic Abstract, and Keywords
"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from report_utils import (
    COLOR_NAVY_RGB, COLOR_SLATE_RGB, COLOR_CHARCOAL_RGB, COLOR_BODY_RGB,
    COLOR_MUTED_RGB, add_h1, add_h2, add_body_p, add_callout_box, create_styled_table
)

def build_title_page(doc: Document):
    """Constructs a formal academic cover page following university standards."""
    # Top spacing
    p_top = doc.add_paragraph()
    p_top.paragraph_format.space_before = Pt(36)
    p_top.paragraph_format.space_after = Pt(0)
    
    # Institution / School Header
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(0)
    p_inst.paragraph_format.space_after = Pt(4)
    r_inst = p_inst.add_run("VELLORE INSTITUTE OF TECHNOLOGY\n")
    r_inst.font.name = "Calibri"
    r_inst.font.size = Pt(15.0)
    r_inst.font.bold = True
    r_inst.font.color.rgb = COLOR_NAVY_RGB
    
    r_dept = p_inst.add_run("SCHOOL OF COMPUTER SCIENCE AND ENGINEERING\nDEPARTMENT OF COMPUTER SCIENCE")
    r_dept.font.name = "Calibri"
    r_dept.font.size = Pt(11.0)
    r_dept.font.bold = True
    r_dept.font.color.rgb = COLOR_SLATE_RGB
    
    # Course / Assignment Meta
    p_course = doc.add_paragraph()
    p_course.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_course.paragraph_format.space_before = Pt(18)
    p_course.paragraph_format.space_after = Pt(24)
    
    r_course = p_course.add_run("BACSE202 – DATABASE MANAGEMENT SYSTEMS\n")
    r_course.font.name = "Calibri"
    r_course.font.size = Pt(13.0)
    r_course.font.bold = True
    r_course.font.color.rgb = COLOR_CHARCOAL_RGB
    
    r_sem = p_course.add_run("FALL SEMESTER 2026–2027 • DIGITAL ASSIGNMENT PROJECT REPORT")
    r_sem.font.name = "Calibri"
    r_sem.font.size = Pt(10.5)
    r_sem.font.color.rgb = COLOR_MUTED_RGB
    
    # Project Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(28)
    p_title.paragraph_format.space_after = Pt(8)
    
    r_title = p_title.add_run("STOCK MARKET ANALYTICS AND PORTFOLIO MANAGEMENT SYSTEM")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(22.0)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_NAVY_RGB
    
    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(36)
    
    r_sub = p_sub.add_run("A High-Performance Hybrid Relational-Timeseries Architecture with Automated Partitioning, Pessimistic Concurrency Control, and Predictive Financial Modeling")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(12.0)
    r_sub.font.italic = True
    r_sub.font.color.rgb = COLOR_SLATE_RGB
    
    # Team Members Block
    p_team_hdr = doc.add_paragraph()
    p_team_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_team_hdr.paragraph_format.space_before = Pt(16)
    p_team_hdr.paragraph_format.space_after = Pt(6)
    r_th = p_team_hdr.add_run("SUBMITTED BY STUDENT TEAM:")
    r_th.font.name = "Calibri"
    r_th.font.size = Pt(10.5)
    r_th.font.bold = True
    r_th.font.color.rgb = COLOR_CHARCOAL_RGB
    
    # Authors Table (Total width: 2.0 + 1.8 + 2.7 = 6.5 inches)
    headers = ["Student Name", "Register Number", "Programme & Specialization"]
    team_data = [
        ["Easwar A P", "25BCE1512", "B.Tech Computer Science and Engineering"],
        ["Mohamed Irfan", "25BCE1462", "B.Tech Computer Science and Engineering"],
        ["Mohammed Nadeem", "25BCE1771", "B.Tech Computer Science and Engineering"]
    ]
    create_styled_table(doc, headers, team_data, [Inches(2.0), Inches(1.8), Inches(2.7)])
    
    # Faculty Guide Block
    p_guide = doc.add_paragraph()
    p_guide.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide.paragraph_format.space_before = Pt(24)
    p_guide.paragraph_format.space_after = Pt(4)
    
    r_gh = p_guide.add_run("UNDER THE ESTEEMED GUIDANCE OF:\n")
    r_gh.font.name = "Calibri"
    r_gh.font.size = Pt(10.5)
    r_gh.font.bold = True
    r_gh.font.color.rgb = COLOR_CHARCOAL_RGB
    
    r_gn = p_guide.add_run("Dr. S. Geetha\n")
    r_gn.font.name = "Calibri"
    r_gn.font.size = Pt(13.0)
    r_gn.font.bold = True
    r_gn.font.color.rgb = COLOR_NAVY_RGB
    
    r_gd = p_guide.add_run("Professor, Department of Computer Science\nSchool of Computer Science and Engineering")
    r_gd.font.name = "Calibri"
    r_gd.font.size = Pt(10.0)
    r_gd.font.color.rgb = COLOR_MUTED_RGB
    
    # Submission Date
    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.paragraph_format.space_before = Pt(20)
    p_date.paragraph_format.space_after = Pt(0)
    r_date = p_date.add_run("NOVEMBER 2026")
    r_date.font.name = "Calibri"
    r_date.font.size = Pt(10.5)
    r_date.font.bold = True
    r_date.font.color.rgb = COLOR_SLATE_RGB
    
    # Page Break to start Table of Contents on Page 2
    doc.add_page_break()


def build_abstract_and_keywords(doc: Document):
    """Renders Section 1 Abstract and Section 2 Keywords."""
    add_h1(doc, "1. Academic Abstract")
    
    add_body_p(
        doc,
        "Modern quantitative financial platforms face an intrinsic architectural dilemma: they must concurrently sustain high-velocity, append-only time-series ingestion for tick and daily market quotations while guaranteeing strict ACID transactional integrity for user accounts, paper trading portfolios, and regulatory mutation audits. Conventional monolithic relational database management systems (RDBMS) experience catastrophic index bloat, lock escalation, and query latency degradation when multi-million row historical price series share tablespaces with transactional ledger entities. Conversely, dedicated NoSQL time-series databases lack foreign key constraints, cross-entity relational joins, and ACID isolation mechanisms essential for multi-asset financial accounting."
    )
    
    add_body_p(
        doc,
        "To resolve this fundamental dichotomy, this project presents the Stock Market Analytics and Portfolio Management System, engineered on a hybrid dual-database architecture. The transactional core is anchored on PostgreSQL 18.4 (running on host port 5435), managing 16 fully normalized relational base tables and 7 analytical views in Boyce-Codd Normal Form (BCNF). User portfolios, cash balances, equity holdings, and trade orders are strictly governed by PostgreSQL row-level pessimistic concurrency controls (SELECT ... FOR UPDATE), composite unique integrity constraints, automated audit triggers, and oversell prevention checks. High-frequency market quotations are decoupled into a dedicated TimescaleDB 2.31.0 engine (PostgreSQL 17.11 container on host port 5434), utilizing native hypertable partitioning across 28 discrete chunks partitioned over 360-day intervals, encompassing 287,310 verified historical price records and 1,653 corporate action events across 49 enterprise equities."
    )
    
    add_body_p(
        doc,
        "The system integrates an asynchronous FastAPI application tier featuring dual connection pooling, intelligent database routing, and automatic failover, coupled with a responsive React 19 single-page application. Furthermore, a predictive analytics subsystem leverages scikit-learn's Histogram-based Gradient Boosting Classifier (HistGradientBoostingClassifier), extracting 20 technical momentum, volatility, and trend indicators to deliver directional next-day price forecasts with 54.12% out-of-sample test accuracy. Rigorous database verification confirms that all 62 relational test suites execute successfully with sub-15ms complex analytical query latencies, validating the robustness, scalability, and academic integrity of the proposed hybrid architecture."
    )
    
    add_callout_box(
        doc,
        "Primary Contribution: Formal proof and production implementation of a decoupled relational-timeseries data tier that eliminates index maintenance overhead on time-series data while preserving strict serializability and auditability for financial ledger transactions.",
        title="CORE RESEARCH CONTRIBUTION"
    )
    
    add_h1(doc, "2. Keywords")
    
    add_body_p(
        doc,
        "Relational Database Management Systems (RDBMS), Time-Series Database (TSDB), TimescaleDB, PostgreSQL, Hypertables, Database Normalization, Boyce-Codd Normal Form (BCNF), Pessimistic Concurrency Control, Row-Level Locking, ACID Properties, Paper Trading, Quantitative Finance, Stock Market Analytics, Gradient Boosting, Foreign Key Integrity, Lossless-Join Decomposition."
    )
    
    # Page break after preliminary Abstract and Keywords
    doc.add_page_break()
